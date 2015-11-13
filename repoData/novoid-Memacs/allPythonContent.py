__FILENAME__ = memacs_csv
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 16:18:15 vk>

from memacs.csv import Csv

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2012-02-24"
PROG_SHORT_DESCRIPTION = u"Memacs for csv files"
PROG_TAG = u"csv"
PROG_DESCRIPTION = u"""
This Memacs module will parse csv files

"""
# set CONFIG_PARSER_NAME only, when you want to have a config file
# otherwise you can comment it out
# CONFIG_PARSER_NAME="memacs-example"
COPYRIGHT_YEAR = "2012-2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>"""


if __name__ == "__main__":
    memacs = Csv(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS
#       use_config_parser_name=CONFIG_PARSER_NAME
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_example
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 16:18:07 vk>

from memacs.example import Foo

PROG_VERSION_NUMBER = u"0.0"
PROG_VERSION_DATE = u"2011-12-18"
PROG_SHORT_DESCRIPTION = u"Memacs for ... "
PROG_TAG = u"mytag"
PROG_DESCRIPTION = u"""
this class will do ....

Then an Org-mode file is generated that contains ....

if youre module needs a config file please give information about usage:

sample config:
[memacs-example]           <-- "memacs-example" has to be CONFIG_PARSER_NAME
foo = 0
bar = 1

"""
# set CONFIG_PARSER_NAME only, when you want to have a config file
# otherwise you can comment it out
# CONFIG_PARSER_NAME="memacs-example"
COPYRIGHT_YEAR = "2011-2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>"""


if __name__ == "__main__":
    memacs = Foo(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS
#       use_config_parser_name=CONFIG_PARSER_NAME
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_filenametimestamps
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2014-01-31 11:11:39 karl.voit>

from memacs.filenametimestamps import FileNameTimeStamps

PROG_VERSION_NUMBER = u"0.3"
PROG_VERSION_DATE = u"2013-12-15"
PROG_SHORT_DESCRIPTION = u"Memacs for file name time stamp"
PROG_TAG = u"filedatestamps"
PROG_DESCRIPTION = u"""This script parses a text file containing absolute paths
to files with ISO datestamps and timestamps in their file names:

Examples:  "2010-03-29T20.12 Divegraph.tiff"
           "2010-12-31T23.59_Cookie_recipies.pdf"
           "2011-08-29T08.23.59_test.pdf"

Emacs tmp-files like file~ are automatically ignored

Then an Org-mode file is generated that contains links to the files.

At files, containing only the date information i.e. "2013-03-08_foo.txt", the
time will be extracted from the filesystem, when both dates are matching. To
Turn off this feature see argument "--skip-file-time-extraction"
"""
COPYRIGHT_YEAR = "2011-2014"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>"""

if __name__ == "__main__":

    memacs = FileNameTimeStamps(prog_version=PROG_VERSION_NUMBER,
                                prog_version_date=PROG_VERSION_DATE,
                                prog_description=PROG_DESCRIPTION,
                                prog_short_description=PROG_SHORT_DESCRIPTION,
                                prog_tag=PROG_TAG,
                                copyright_year=COPYRIGHT_YEAR,
                                copyright_authors=COPYRIGHT_AUTHORS)
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_git
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 16:18:40 vk>

from memacs.git import GitMemacs

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2011-12-20"
PROG_SHORT_DESCRIPTION = u"Memacs for git files "
PROG_TAG = u"git"
PROG_DESCRIPTION = u"""
This class will parse files from git rev-parse output

use following command to generate input file
$ git rev-list --all --pretty=raw > /path/to/input file

Then an Org-mode file is generated that contains all commit message

If outputfile is specified, only non-existing commits are appended
"""
COPYRIGHT_YEAR = "2011-2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>"""


if __name__ == "__main__":
    memacs = GitMemacs(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_ical
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 16:18:50 vk>

from memacs.ical import CalendarMemacs

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2011-12-28"
PROG_SHORT_DESCRIPTION = u"Memacs for ical Calendars"
PROG_TAG = u"calendar"
PROG_DESCRIPTION = u"""This script parses a *.ics file and generates
Entries for VEVENTS
* other's like VALARM are not implemented by now
"""
COPYRIGHT_YEAR = "2011-2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>"""

if __name__ == "__main__":
    memacs = CalendarMemacs(prog_version=PROG_VERSION_NUMBER,
                            prog_version_date=PROG_VERSION_DATE,
                            prog_description=PROG_DESCRIPTION,
                            prog_short_description=PROG_SHORT_DESCRIPTION,
                            prog_tag=PROG_TAG,
                            copyright_year=COPYRIGHT_YEAR,
                            copyright_authors=COPYRIGHT_AUTHORS
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_imap
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 16:19:02 vk>

from memacs.imap import ImapMemacs

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2011-12-30"
PROG_SHORT_DESCRIPTION = u"Memacs for imap emails"
PROG_TAG = u"emails:imap"
PROG_DESCRIPTION = u"""The memacs module will connect to an IMAP Server,
fetch all mails of given folder (-f or --folder-name <folder>),
parses the mails and writes them to an orgfile.

This module uses configfiles (-c, --config-file <path>)

sample-config:

[memacs-imap]
host = imap.gmail.com
port = 993
user = foo@gmail.com
password = bar
"""
CONFIG_PARSER_NAME = "memacs-imap"
COPYRIGHT_YEAR = "2011-2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>"""


if __name__ == "__main__":
    memacs = ImapMemacs(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS,
        use_config_parser_name=CONFIG_PARSER_NAME
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_phonecalls
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 16:19:18 vk>

from memacs.phonecalls import PhonecallsMemacs

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2012-03-08"
PROG_SHORT_DESCRIPTION = u"Memacs for phonecalls"
PROG_TAG = u"phonecalls"
PROG_DESCRIPTION = u"""
This Memacs module will parse output of phonecalls xml backup files

sample xml file:
<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<calls count="8">
  <call number="+43691234123" duration="59" date="1312563906092" type="1" />
  <call number="06612341234" duration="22" date="1312541215834" type="2" />
  <call number="-1" duration="382" date="1312530691081" type="1" />
  <call number="+4312341234" duration="289" date="1312482327195" type="1" />
  <call number="+4366412341234" duration="70" date="1312476334059" type="1" />
  <call number="+4366234123" duration="0" date="1312473751975" type="2" />
  <call number="+436612341234" duration="0" date="1312471300072" type="3" />
  <call number="+433123412" duration="60" date="1312468562489" type="2" />
</calls>

Then an Org-mode file is generated.
"""
COPYRIGHT_YEAR = "2011-2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>"""

if __name__ == "__main__":
    memacs = PhonecallsMemacs(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_phonecalls_superbackup
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-09-12 09:11 igb>

from memacs.phonecalls_superbackup import PhonecallsSuperBackupMemacs

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2012-03-08"
PROG_SHORT_DESCRIPTION = u"Memacs for phonecalls"
PROG_TAG = u"phonecalls"
PROG_DESCRIPTION = u"""
This Memacs module will parse output of phonecalls xml backup files

sample xml file:
<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<calls count="8">
  <call number="+43691234123" duration="59" date="1312563906092" type="1" />
  <call number="06612341234" duration="22" date="1312541215834" type="2" />
  <call number="-1" duration="382" date="1312530691081" type="1" />
  <call number="+4312341234" duration="289" date="1312482327195" type="1" />
  <call number="+4366412341234" duration="70" date="1312476334059" type="1" />
  <call number="+4366234123" duration="0" date="1312473751975" type="2" />
  <call number="+436612341234" duration="0" date="1312471300072" type="3" />
  <call number="+433123412" duration="60" date="1312468562489" type="2" />
</calls>

Then an Org-mode file is generated.
"""
COPYRIGHT_YEAR = "2011-2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>
Ian Barton <ian@manor-farm.org>"""

if __name__ == "__main__":
    memacs = PhonecallsSuperBackupMemacs(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_photos
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 16:19:39 vk>

from memacs.photos import PhotosMemacs

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2012-03-10"
PROG_SHORT_DESCRIPTION = u"Memacs for photos (exif)"
PROG_TAG = u"photos"
PROG_DESCRIPTION = u"""

This memacs module will walk through a given folder looking for photos.
If a photo is found, it will get a timestamp from the  exif information.

Then an Org-mode file is generated.
"""
COPYRIGHT_YEAR = "2012-2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>"""

if __name__ == "__main__":
    memacs = PhotosMemacs(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_rss
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 16:19:47 vk>

from memacs.rss import RssMemacs

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2011-12-27"
PROG_SHORT_DESCRIPTION = u"Memacs for rss feeds"
PROG_TAG = u"rss"
PROG_DESCRIPTION = u"""
This Memacs module will parse rss files.

rss can be read from file (-f FILE) or url (-u URL)

The items are automatically be appended to the org file.


Attention: RSS2.0 is required

Sample Org-entries
: ** <2009-09-06 Sun 18:45> [[http://www.wikipedia.org/][link]]: Example entry
:   Here is some text containing an interesting description.
:   :PROPERTIES:
:   :LINK:    [[http://www.wikipedia.org/]]
:   :GUID:    rss guid
:   :SUMMARY: Here is some text containing an interesting description.
:   :ID:      unique string per item
:   :END:
"""
COPYRIGHT_YEAR = "2011-2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>"""


if __name__ == "__main__":
    memacs = RssMemacs(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_simplephonelogs
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 18:50:29 vk>

from memacs.simplephonelogs import SimplePhoneLogsMemacs

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2013-04-04"
PROG_SHORT_DESCRIPTION = u"Memacs for simple phone logs"
PROG_TAG = u"phonelog"
PROG_DESCRIPTION = u"""
This Memacs module will parse simple log files which were written
for example by Tasker.

sample log file: (DATE # TIME # WHAT # BATTERYSTATE # UPTIMESECONDS)
2012-11-20 # 11.56 # boot     #   89 # 6692
2012-11-20 # 11.56 # boot     #   89 # 6694
2012-11-20 # 19.59 # shutdown #   72 # 35682
2012-11-20 # 21.32 # boot     #   71 # 117
2012-11-20 # 23.52 # shutdown #  63 # 8524
2012-11-21 # 07.23 # boot # 100 # 115
2012-11-21 # 07.52 # wifi-home # 95 # 1879
2012-11-21 # 08.17 # wifi-home-end # 92 # 3378
2012-11-21 # 13.06 # boot # 77 # 124
2012-11-21 # 21.08 # wifi-home # 50 # 29033
2012-11-22 # 00.12 # shutdown #  39 # 40089
2012-11-29 # 08.47 # boot # 100 # 114
2012-11-29 # 08.48 # wifi-home # 100 # 118
2012-11-29 # 09.41 # wifi-home-end # 98 # 3317
2012-11-29 # 14.46 # wifi-office # 81 # 21633
2012-11-29 # 16.15 # wifi-home # 76 # 26955
2012-11-29 # 17.04 # wifi-home-end # 74 # 29912
2012-11-29 # 23.31 # shutdown #  48 # 53146

Then an Org-mode file is generated accordingly.
"""
COPYRIGHT_YEAR = "2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>"""

if __name__ == "__main__":
    memacs = SimplePhoneLogsMemacs(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_sms
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 16:19:53 vk>

from memacs.sms import SmsMemacs

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2012-03-07"
PROG_SHORT_DESCRIPTION = u"Memacs for sms"
PROG_TAG = u"sms"
PROG_DESCRIPTION = u"""
This Memacs module will parse output of sms xml backup files

> A sample xml file you find in the documentation file memacs_sms.org.

Then an Org-mode file is generated.
"""
COPYRIGHT_YEAR = "2011-2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>"""

if __name__ == "__main__":
    memacs = SmsMemacs(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_sms_superbackup
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-09-12 09:11 igb>

from memacs.sms_superbackup import SmsSuperBackupMemacs

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2012-03-07"
PROG_SHORT_DESCRIPTION = u"Memacs for sms"
PROG_TAG = u"sms"
PROG_DESCRIPTION = u"""
This Memacs module will parse output of sms xml backup files

> A sample xml file you find in the documentation file memacs_sms.org.

Then an Org-mode file is generated.
"""
COPYRIGHT_YEAR = "2011-2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>
Ian Barton <ian@manor-farm.org>"""

if __name__ == "__main__":
    memacs = SmsSuperBackupMemacs(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_svn
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 16:20:01 vk>

from memacs.svn import SvnMemacs

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2011-12-27"
PROG_SHORT_DESCRIPTION = u"Memacs for svn"
PROG_TAG = u"svn"
PROG_DESCRIPTION = u"""
This Memacs module will parse output of svn log --xml

sample xml:
 <?xml version="1.0"?>
    <log>
    <logentry
       revision="13">
    <author>bob</author>
    <date>2011-11-05T18:18:22.936127Z</date>
    <msg>Bugfix.</msg>
    </logentry>
    </log>

Then an Org-mode file is generated that contains information
about the log messages, author, and revision
"""
COPYRIGHT_YEAR = "2011-2013"
COPYRIGHT_AUTHORS = """Karl Voit <tools@Karl-Voit.at>,
Armin Wieser <armin.wieser@gmail.com>"""

if __name__ == "__main__":
    memacs = SvnMemacs(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_twitter
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 16:18:07 vk>

from memacs.twitter import Twitter

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2013-09-01"
PROG_SHORT_DESCRIPTION = u"Memacs for Twitter "
PROG_TAG = u"mytag"
PROG_DESCRIPTION = u"""
This Memacs module will process your Twitter timeline ....


sample config:
[memacs-twitter]           <-- "memacs-example" has to be CONFIG_PARSER_NAME
APP_KEY =
APP_SECRET =
OAUTH_TOKEN =
OAUTH_TOKEN_SECRET =
screen_name =
count =


"""
# set CONFIG_PARSER_NAME only, when you want to have a config file
# otherwise you can comment it out
CONFIG_PARSER_NAME="memacs-twitter"
COPYRIGHT_YEAR = "2013"
COPYRIGHT_AUTHORS = """Ian Barton <ian@manor-farm.org>"""


if __name__ == "__main__":
    memacs = Twitter(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS,
        use_config_parser_name=CONFIG_PARSER_NAME
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = memacs_twitter
#!/home/ian/.virtualenvs/my_env/bin/python2
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-04 16:18:07 vk>

from memacs.twitter import Twitter

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2013-09-01"
PROG_SHORT_DESCRIPTION = u"Memacs for Twitter "
PROG_TAG = u"mytag"
PROG_DESCRIPTION = u"""
This Memacs module will process your Twitter timeline ....


sample config:
[memacs-twitter]           <-- "memacs-example" has to be CONFIG_PARSER_NAME
APP_KEY =
APP_SECRET =
OAUTH_TOKEN =
OAUTH_TOKEN_SECRET =
screen_name =


"""
# set CONFIG_PARSER_NAME only, when you want to have a config file
# otherwise you can comment it out
CONFIG_PARSER_NAME="memacs-twitter"
COPYRIGHT_YEAR = "2013"
COPYRIGHT_AUTHORS = """Ian Barton <ian@manor-farm.org>"""


if __name__ == "__main__":
    memacs = Twitter(
        prog_version=PROG_VERSION_NUMBER,
        prog_version_date=PROG_VERSION_DATE,
        prog_description=PROG_DESCRIPTION,
        prog_short_description=PROG_SHORT_DESCRIPTION,
        prog_tag=PROG_TAG,
        copyright_year=COPYRIGHT_YEAR,
        copyright_authors=COPYRIGHT_AUTHORS,
        use_config_parser_name=CONFIG_PARSER_NAME
        )
    memacs.handle_main()

########NEW FILE########
__FILENAME__ = csv
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2011-12-30 03:38:09 armin>

import logging
import time
import os
import sys
from lib.orgformat import OrgFormat
from lib.memacs import Memacs
from lib.reader import UnicodeCsvReader
from lib.orgproperty import OrgProperties


class Csv(Memacs):
    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        self._parser.add_argument(
           "-f", "--file", dest="csvfile",
           action="store",
           help="input csv file")

        self._parser.add_argument(
           "-d", "--delimiter", dest="delimiter",
           action="store",
           help="delimiter, default \";\"")

        self._parser.add_argument(
           "-e", "--encoding", dest="encoding",
           action="store",
           help="default encoding utf-8, see " + \
           "http://docs.python.org/library/codecs.html#standard-encodings" + \
           "for possible encodings")

        self._parser.add_argument(
           "-ti", "--timestamp-index", dest="timestamp_index",
           action="store",
           help="on which column is timestamp?")

        self._parser.add_argument(
           "-tf", "--timestamp-format", dest="timestamp_format",
           action="store",
           #help="format of the timestamp, i.e. \"%d.%m.%Y %H:%M:%S:%f\" " + \
           help="format of the timestamp, i.e. " + \
           "\"%%d.%%m.%%Y %%H:%%M:%%S:%%f\" " + \
           "for  \"14.02.2012 10:22:37:958\" see " + \
           "http://docs.python.org/library/time.html#time.strftime" + \
           "for possible formats")

        self._parser.add_argument(
           "-oi", "--output-indices", dest="output_indices",
           action="store",
           help="indices to use for output i.e. \"1 2 3\"")

    def _parser_parse_args(self):
        """
        overwritten method of class Memacs

        all additional arguments are parsed in here
        """
        Memacs._parser_parse_args(self)
        if not self._args.csvfile:
            self._parser.error("please specify input csv file")
        if not (os.path.exists(self._args.csvfile) or \
            os.access(self._args.csvfile, os.R_OK)):
            self._parser.error("input file not found or not readable")

        if self._args.delimiter:
            self._args.delimiter = self._args.delimiter
        else:
            self._args.delimiter = ";"

        if not self._args.encoding:
            self._args.encoding = "utf-8"

        if not self._args.timestamp_index:
            self._parser.error("need to know timestamp index")
        else:
            try:
                self._args.timestamp_index = int(self._args.timestamp_index)
            except ValueError:
                self._parser.error("timestamp index not an int")

        if not self._args.timestamp_format:
            self._parser.error("need to know timestamp format")

        if not self._args.output_indices:
            self._parser.error("need to know output indices")
        else:
            try:
                self._args.output_indices = map(
                    int, self._args.output_indices.split())
            except ValueError:
                self._parser.error("output-indices must have " + \
                                   "following format i.e: \"1 2 3\"")

    def _main(self):
        """
        get's automatically called from Memacs class
        """

        with open(self._args.csvfile, 'rb') as f:
            try:
                for row in UnicodeCsvReader(f, encoding=self._args.encoding,
                                         delimiter=self._args.delimiter):
                    logging.debug(row)
                    try:
                        tstamp = time.strptime(row[self._args.timestamp_index],
                                               self._args.timestamp_format)
                    except ValueError, e:
                        logging.error("timestamp-format does not match: %s",
                                      e)
                        sys.exit(1)
                    except IndexError, e:
                        logging.error("did you specify the right delimiter?",
                                      e)
                        sys.exit(1)

                    timestamp = OrgFormat.datetime(tstamp)

                    output = []
                    for i in self._args.output_indices:
                        output.append(row[i])
                    output = " ".join(output)

                    data_for_hashing = "".join(row)

                    properties = OrgProperties(
                            data_for_hashing=data_for_hashing)

                    self._writer.write_org_subitem(timestamp=timestamp,
                                                   output=output,
                                                   properties=properties,
                                                   )
            except UnicodeDecodeError, e:
                logging.error("could not decode file in utf-8," + \
                              "please specify input encoding")
                sys.exit(1)

########NEW FILE########
__FILENAME__ = example
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2012-03-09 15:48:38 armin>

import logging
import time
from lib.orgproperty import OrgProperties
from lib.orgformat import OrgFormat
from lib.memacs import Memacs


class Foo(Memacs):
    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        #self._parser.add_argument(
        #   "-e", "--example", dest="example",
        #   action="store_true",
        #   help="path to a folder to search for filenametimestamps, " +
        #   "multiple folders can be specified: -f /path1 -f /path2")

        #self._parser.add_argument(
        #   "-i", "--int", dest="example_int",
        #   action="store_true",
        #   help="example2",
        #   type=int)

    def _parser_parse_args(self):
        """
        overwritten method of class Memacs

        all additional arguments are parsed in here
        """
        Memacs._parser_parse_args(self)
        # if self._args.example == ...:
        #     self._parser.error("could not parse foo")

    def _main(self):
        """
        get's automatically called from Memacs class
        """
        # do all the stuff

        # if you need something from config:
        # attention: foo will be unicode
        # foo = self._get_config_option("foo")

        logging.info("foo started")

        # how to handle config files ?
        # sample config file:
        # ---------8<-----------
        # [memacs-example]
        # foo = 0
        # bar = 1
        # --------->8-----------
        # to read it out, just do following:
        # foo = self._get_config_option("foo")
        # bar = self._get_config_option("bar")

        # use logging.debug() for debug messages
        # use logging.error() for error messages
        # use logging.info() instead of print for informing user
        #
        # on an fatal error:
        # use logging.error() and sys.exit(1)

        timestamp = OrgFormat.datetime(time.gmtime(0))
        # note: timestamp has to be a struct_time object

        # Orgproperties
        # Option 1: no properties given, specify argument for hashing data
        properties = OrgProperties("hashing data :ALKJ!@# should be unique")
        # Option 2: add properties which are all-together unique
        # properties.add("Category","fun")
        # properties.add("from","me@example.com")
        # properties.add("body","foo")

        self._writer.write_org_subitem(timestamp=timestamp,
                                       output="foo",
                                       properties=properties)

        # writes following:
        #** <1970-01-01 Thu 00:00> foo
        #   :PROPERTIES:
        #   :ID:             da39a3ee5e6b4b0d3255bfef95601890afd80709
        #   :END:

        notes = "bar notes\nfoo notes"

        p = OrgProperties(data_for_hashing="read comment below")
        # if a hash is not unique only with its :PROPERTIES: , then
        # set data_for_hasing string additional information i.e. the output
        # , which then makes the hash really unique
        #
        # if you *really*, *really* have already a unique id,
        # then you can call following method:
        # p.set_id("unique id here")

        p.add("DESCRIPTION", "foooo")
        p.add("foo-property", "asdf")

        tags = [u"tag1", u"tag2"]

        self._writer.write_org_subitem(timestamp=timestamp,
                                       output="bar",
                                       note=notes,
                                       properties=p,
                                       tags=tags)
        # writes following:
        #** <1970-01-01 Thu 00:00> bar    :tag1:tag2:
        #   bar notes
        #   foo notes
        #   :PROPERTIES:
        #   :DESCRIPTION:    foooo
        #   :FOO-PROPERTY:   asdf
        #   :ID:             97521347348df02dab8bf86fbb6817c0af333a3f
        #   :END:

########NEW FILE########
__FILENAME__ = filenametimestamps
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2014-03-13 17:32:22 karl.voit>

import os
from lib.memacs import Memacs
from lib.orgformat import OrgFormat
from lib.orgformat import TimestampParseException
from lib.orgproperty import OrgProperties
import re
import logging
import time
import sys
import codecs

DATESTAMP_REGEX = re.compile("([12]\d{3})-([01]\d)-([0123]\d)")
TIMESTAMP_REGEX = re.compile("([12]\d{3})-([01]\d)-([0123]\d)T([012]\d)" + \
                             "[.]([012345]\d)([.]([012345]\d))?")


class FileNameTimeStamps(Memacs):

    def _parser_add_arguments(self):
        Memacs._parser_add_arguments(self)

        self._parser.add_argument("-f", "--folder",
                                  dest="filenametimestamps_folder",
                                  action="append",
                                  help="path to a folder to search for " + \
                                      "filenametimestamps, " + \
                                  "multiple folders can be specified: " + \
                                      "-f /path1 -f /path2")

        self._parser.add_argument("-x", "--exclude", dest="exclude_folder",
                        help="path to excluding folder, for more excludes " + \
                             "use this: -x /path/exclude -x /path/exclude")

        self._parser.add_argument("--filelist", dest="filelist",
                        help="file containing a list of files to process. " + \
                             "either use \"--folder\" or the \"--filelist\" argument, not both.")

        self._parser.add_argument("--ignore-non-existing-items",
                                  dest="ignore_nonexisting", action="store_true",
                                  help="ignores non-existing files or folders within filelist")

        self._parser.add_argument("-l", "--follow-links",
                                  dest="follow_links", action="store_true",
                                  help="follow symbolics links," + \
                                      " default False")

        self._parser.add_argument("--skip-file-time-extraction",
                                  dest="skip_filetime_extraction",
                                  action="store_true",
                                  help="skip extraction of the file time " + \
                                  " in files containing only the date in " + \
                                  "the filename"
        )

    def _parser_parse_args(self):
        Memacs._parser_parse_args(self)

        if self._args.filenametimestamps_folder and self._args.filelist:
            self._parser.error("You gave both \"--filelist\" and \"--folder\" argument. Please use either or.\n")

        if not self._args.filelist and not self._args.filenametimestamps_folder:
            self._parser.error("no filenametimestamps_folder specified")

        if self._args.filelist:
            if not os.path.isfile(self._args.filelist):
                self._parser.error("Check the filelist argument: " + \
                                       "[" + str(self._args.filelist) + "] is not an existing file")

        if self._args.filenametimestamps_folder:
            for f in self._args.filenametimestamps_folder:
                if not os.path.isdir(f):
                    self._parser.error("Check the folderlist argument: " + \
                                           "[" + str(f) + "] and probably more aren't folders")

    def __ignore_dir(self, ignore_dir):
        """
        @param ignore_dir: should this ignore_dir be ignored?
        @param return: true  - if ignore_dir should be ignored
                       false - otherwise
        """
        if self._args.exclude_folder and \
        ignore_dir in self._args.exclude_folder:
            logging.info("ignoring ignore_dir: " + ignore_dir)
            return True
        else:
            return False

    def __handle_folder(self, folder):
        """
        walks through a folder
        """
        for rootdir, dirs, files in os.walk(folder,
                                        followlinks=self._args.follow_links):
            if not self.__ignore_dir(rootdir):
                for file in files:
                    self.__handle_file(file, rootdir)

    def __parse_and_write_file(self, file, link):
        """
        Parses the date+time and writes entry to outputfile

        @param file: filename
        @param link: path
        """
        if TIMESTAMP_REGEX.match(file):
            # if we found a timestamp too,take hours,min
            # and optionally seconds from this timestamp
            timestamp = TIMESTAMP_REGEX.match(file).group()
            orgdate = OrgFormat.strdatetimeiso8601(timestamp)
            logging.debug("found timestamp: " + orgdate)
        else:
            datestamp = DATESTAMP_REGEX.match(file).group()
            orgdate = OrgFormat.strdate(datestamp)
            orgdate_time_tupel = OrgFormat.datetupeliso8601(datestamp)

            if self._args.skip_filetime_extraction != True:            

                if os.path.exists(link):
                  file_datetime = time.localtime(os.path.getmtime(link))
                  # check if the file - time information matches year,month,day,
                  # then update time
                  if file_datetime.tm_year == orgdate_time_tupel.tm_year and \
                     file_datetime.tm_mon == orgdate_time_tupel.tm_mon and \
                     file_datetime.tm_mday == orgdate_time_tupel.tm_mday:
                  
                      logging.debug("found a time in file.setting %s-->%s",
                                    orgdate, OrgFormat.date(file_datetime, True))
                      orgdate = OrgFormat.date(file_datetime, True)
                else:
                    logging.debug("item [%s] not found and thus could not determine mtime" % link)

        # write entry to org file (omit replacement of spaces in file names)
        output = OrgFormat.link(link=link, description=file, replacespaces=False)
        # we need optional data for hashing due it can be, that more
        # than one file have the same timestamp
        properties = OrgProperties(data_for_hashing=output)
        self._writer.write_org_subitem(timestamp=orgdate,
                                       output=output,
                                       properties=properties)

    def __handle_file(self, file, rootdir):
        """
        handles a file
        """
        # don't handle emacs tmp files (file~)
        if DATESTAMP_REGEX.match(file) and file[-1:] != '~':
            link = os.path.join(rootdir, file)
            logging.debug(link)
            try:
                # we put this in a try block because:
                # if a timestamp is false i.e. 2011-14-19 or false time
                # we can handle those not easy with REGEX, therefore we have
                # an Exception TimestampParseException, which is thrown,
                # wen strptime (parse from string to time tupel) fails
                self.__parse_and_write_file(file, link)
            except TimestampParseException, e:
                logging.warning("False date(time) in file: %s", link)

    def _main(self):

        if self._args.filenametimestamps_folder:

            for folder in self._args.filenametimestamps_folder:
                self.__handle_folder(folder)

        elif self._args.filelist:

            for rawitem in codecs.open(self._args.filelist, "r", "utf-8"):

                item = rawitem.strip()

                if not os.path.exists(item):
                    if self._args.ignore_nonexisting:
                        logging.debug("File or folder does not exist: [%s] (add due to set ignore-nonexisting argument)", item)
                        self.__handle_file(os.path.basename(item), os.path.dirname(item))
                    else:
                        logging.warning("File or folder does not exist: [%s]", item)
                else:
                    self.__handle_file(os.path.basename(item), os.path.dirname(item))

        else:
            logging.error("\nERROR: You did not provide \"--filelist\" nor \"--folder\" argument. Please use one of them.\n")
            sys.exit(3)

########NEW FILE########
__FILENAME__ = git
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2012-04-16 18:24:28 armin>

import sys
import os
import logging
import time
import codecs
from lib.orgproperty import OrgProperties
from lib.orgformat import OrgFormat
from lib.memacs import Memacs


class Commit(object):
    """
    class for representing one commit
    """

    def __init__(self):
        """
        Ctor
        """
        self.__empty = True
        self.__subject = ""
        self.__body = ""
        self.__timestamp = ""
        self.__author = ""
        self.__properties = OrgProperties()

    def __set_author_timestamp(self, line):
        """
        extracts the date + time from line:
        author Forename Lastname <mail> 1234567890 +0000
        @param line
        """
        self.__empty = False
        date_info = line[-16:]  # 1234567890 +0000
        seconds_since_epoch = float(date_info[:10])
        #timezone_info = date_info[11:]
        self.__timestamp = OrgFormat.datetime(
                            time.localtime(seconds_since_epoch))
        self.__author = line[7:line.find("<")].strip()

    def add_header(self, line):
        """
        adds line to the header

        if line contains "author" this method
        calls self.__set_author_timestamp(line)
        for setting right author + datetime created

        every line will be added as property
        i.e:
        commit <hashtag>
        would then be following property:
        :COMMIT: <hashtag>
        @param line:
        """
        self.__empty = False

        if line != "":
            whitespace = line.find(" ")
            tag = line[:whitespace].upper()
            value = line[whitespace:]
            self.__properties.add(tag, value)

            if tag == "AUTHOR":
                self.__set_author_timestamp(line)

    def add_body(self, line):
        """
        adds a line to the body

        if line starts with Signed-off-by,
        also a property of that line is added
        """

        line = line.strip()
        if line != "":
            if line[:14] == "Signed-off-by:":
                self.__properties.add("SIGNED-OFF-BY", line[15:])
            elif self.__subject == "":
                self.__subject = line
            else:
                self.__body += line + "\n"

    def is_empty(self):
        """
        @return: True  - empty commit
                 False - not empty commit
        """
        return self.__empty

    def get_output(self):
        """
        @return tupel: output,properties,body for Orgwriter.write_sub_item()
        """
        output = self.__author + ": " + self.__subject
        return output, self.__properties, self.__body, self.__author, \
                self.__timestamp


class GitMemacs(Memacs):
    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        self._parser.add_argument(
           "-f", "--file", dest="gitrevfile",
           action="store",
           help="path to a an file which contains output from " + \
           " following git command: git rev-list --all --pretty=raw")

        self._parser.add_argument(
           "-g", "--grep-user", dest="grepuser",
           action="store",
           help="if you wanna parse only commit from a specific person. " + \
           "format:<Forname Lastname> of user to grep")

        self._parser.add_argument(
           "-e", "--encoding", dest="encoding",
           action="store",
           help="default encoding utf-8, see " + \
           "http://docs.python.org/library/codecs.html#standard-encodings" + \
           "for possible encodings")

    def _parser_parse_args(self):
        """
        overwritten method of class Memacs

        all additional arguments are parsed in here
        """
        Memacs._parser_parse_args(self)
        if self._args.gitrevfile and not \
                (os.path.exists(self._args.gitrevfile) or \
                     os.access(self._args.gitrevfile, os.R_OK)):
            self._parser.error("input file not found or not readable")

        if not self._args.encoding:
            self._args.encoding = "utf-8"

    def get_line_from_stream(self, input_stream):
        try:
            return input_stream.readline()
        except UnicodeError, e:
            logging.error("Can't decode to encoding %s, " + \
                          "use argument -e or --encoding see help",
                          self._args.encoding)
            sys.exit(1)

    def _main(self):
        """
        get's automatically called from Memacs class
        read the lines from git-rev-list file,parse and write them to org file
        """

        # read file
        if self._args.gitrevfile:
            logging.debug("using as %s input_stream",
                          self._args.gitrevfile)
            input_stream = codecs.open(self._args.gitrevfile,
                                       encoding=self._args.encoding)
        else:
            logging.debug("using sys.stdin as input_stream")
            input_stream = codecs.getreader(self._args.encoding)(sys.stdin)

        # now go through the file
        # Logic (see example commit below)
        # first we are in an header and not in an body
        # every newline toggles output
        # if we are in body then add the body to commit class
        # if we are in header then add the header to commit class
        #
        # commit 6fb35035c5fa7ead66901073413a42742a323e89
        # tree 7027c628031b3ad07ad5401991f5a12aead8237a
        # parent 05ba138e6aa1481db2c815ddd2acb52d3597852f
        # author Armin Wieser <armin.wieser@example.com> 1324422878 +0100
        # committer Armin Wieser <armin.wieser@example.com> 1324422878 +0100
        #
        #     PEP8
        #     Signed-off-by: Armin Wieser <armin.wieser@gmail.com>

        was_in_body = False
        commit = Commit()
        commits = []

        line = self.get_line_from_stream(input_stream)

        while line:
            line = line.rstrip()  # removing \n
            logging.debug("got line: %s", line)
            if line.strip() == "" or len(line) != len(line.lstrip()):
                commit.add_body(line)
                was_in_body = True
            else:
                if was_in_body:
                    commits.append(commit)
                    commit = Commit()
                commit.add_header(line)
                was_in_body = False

            line = self.get_line_from_stream(input_stream)

        # adding last commit
        if not commit.is_empty():
            commits.append(commit)

        logging.debug("got %d commits", len(commits))
        if len(commits) == 0:
            logging.error("Is there an error? Because i found no commits.")

        # time to write all commits to org-file
        for commit in commits:
            output, properties, note, author, timestamp = commit.get_output()

            if not(self._args.grepuser) or \
            (self._args.grepuser and self._args.grepuser == author):
                # only write to stream if
                # * grepuser is not set or
                # * grepuser is set and we got an entry with the right author
                self._writer.write_org_subitem(output=output,
                                               timestamp=timestamp,
                                               properties=properties,
                                               note=note)

        if self._args.gitrevfile:
            input_stream.close()

########NEW FILE########
__FILENAME__ = ical
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2012-05-24 19:18:21 armin>

import sys
import os
import logging
import time
from lib.memacs import Memacs
from lib.orgformat import OrgFormat
from lib.orgproperty import OrgProperties
from lib.reader import CommonReader

try:
    from icalendar import Calendar
except ImportError, e:
    print "please install python package \"icalendar\""
    print e
    sys.exit(3)


class CalendarMemacs(Memacs):
    def _parser_add_arguments(self):
        self._parser.add_argument("-c", "--calendar-url", dest="calendar_url",
                        help="url to calendar")

        self._parser.add_argument("-cf", "--calendar-file",
                                  dest="calendar_file",
                                  help="path to calendar")

        self._parser.add_argument(
            "-x", "--exclude", dest="excludelist",
            help="path to one or more folders seperated with \"|\"," + \
                "i.e.:\"/path/to/folder1|/path/to/folder2|..\"")

    def _parser_parse_args(self):
        Memacs._parser_parse_args(self)

        if not self._args.calendar_url and not self._args.calendar_file:
            self._parser.error("specify a calendar url or calendar file")

        if self._args.calendar_url and self._args.calendar_file:
            self._parser.error(
                "only set a url or path to a calendar not both.")

        if self._args.calendar_file  \
        and not os.path.exists(self._args.calendar_file):
            self._parser.error("calendar path not exists")

    def __handle_vcalendar(self, component):
        """
        handles a VCALENDAR Component

        sets timezone to calendar's timezone

        @param component: icalendar component
        """
        # Set timezone
        timezone = component.get('x-wr-timezone')
        logging.debug("Setting timezone to: " + timezone)
        os.environ['TZ'] = timezone
        time.tzset()

    def __handle_rrule(self, component):
        """
        Handles calendars rrule (used for reoccuring events)

        returns org string for reoccuring date
        """
        freq = self.__vtext_to_unicode(component.get('freq'))

        if freq == "MINUTELY":
            raise NotImplemented
        elif freq == "HOURLY":
            raise NotImplemented
        elif freq == "DAILY":
            return "+1d"
        elif freq == "WEEKLY":
            return "+1w"
        elif freq == "YEARLY":
            return "+1y"
        else:
            return ""

    def __vtext_to_unicode(self, vtext, nonetype=None):
        """
        @return unicode-string
                None: otherwise
        """
        if vtext:
            return unicode(vtext)
        else:
            return nonetype

    def __get_datetime_range(self, dtstart, dtend):
        """
        @return string: Datetime - Range in Org Format
        """
        begin_tupel = OrgFormat.datetupelutctimestamp(dtstart)
        end_tupel = OrgFormat.datetupelutctimestamp(dtend)

        # handle "all-day" - events
        if begin_tupel.tm_sec == 0 and \
                begin_tupel.tm_min == 0 and \
                begin_tupel.tm_hour == 0 and \
                end_tupel.tm_sec == 0 and \
                end_tupel.tm_min == 0 and \
                end_tupel.tm_hour == 0:
            # we have to subtract 1 day to get the correct dates
            end_tupel = time.localtime(time.mktime(end_tupel) - 24 * 60 * 60)

        return OrgFormat.utcrange(begin_tupel, end_tupel)

    def __handle_vevent(self, component):
        """
        handles a VCALENDAR Component

        sets timezone to calendar's timezone

        @param component: icalendar component
        """

        logging.debug(component)
        summary = self.__vtext_to_unicode(component.get('summary'),
                                          nonetype="")
        location = self.__vtext_to_unicode(component.get('location'))
        description = self.__vtext_to_unicode(component.get('description'))
        # format: 20091207T180000Z or 20100122
        dtstart = self.__vtext_to_unicode(component.get('DTSTART').to_ical())
        # format: 20091207T180000Z or 20100122
        dtend = self.__vtext_to_unicode(component.get('DTEND').to_ical())

        # format: 20091207T180000Z
        # not used: Datestamp created
        #dtstamp = self.__vtext_to_unicode(component.get('dtstamp'))

        # handle repeating events
        # not implemented due to org-mode datestime-range cannot be repeated
        # component.get('rrule')

        orgdate = self.__get_datetime_range(dtstart, dtend)

        logging.debug(orgdate + " " + summary)

        # we need to set data_for_hashing=summary to really get a other sha1
        data_for_hashing = orgdate + summary

        org_properties = OrgProperties(data_for_hashing=data_for_hashing)

        if location != None:
            org_properties.add("LOCATION", location)
        if description != None:
            org_properties.add("DESCRIPTION", description)

        self._writer.write_org_subitem(output=summary,
                                       properties=org_properties,
                                       timestamp=orgdate)

    def _main(self):
        # getting data
        if self._args.calendar_file:
            data = CommonReader.get_data_from_file(self._args.calendar_file,
            encoding=None)
        elif self._args.calendar_url:
            data = CommonReader.get_data_from_url(self._args.calendar_url)

        # read and go through calendar
        cal = Calendar.from_ical(data)
        for component in cal.walk():
            if component.name == "VCALENDAR":
                self.__handle_vcalendar(component)
            elif component.name == "VEVENT":
                self.__handle_vevent(component)
            else:
                logging.debug("Not handling component: " + component.name)

########NEW FILE########
__FILENAME__ = imap
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2012-09-06 19:54:04 armin>

import sys
import os
import logging
import imaplib
from lib.memacs import Memacs
from lib.mailparser import MailParser


class ImapMemacs(Memacs):
    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        self._parser.add_argument(
           "-l", "--list-folders",
           dest="list_folders",
           action="store_true",
           help="show possible folders of connection")

        self._parser.add_argument(
           "-f", "--folder_name",
           dest="folder_name",
           help="name of folder to get emails from, " + \
            "when you don't know name call --list-folders")

    def _parser_parse_args(self):
        """
        overwritten method of class Memacs

        all additional arguments are parsed in here
        """
        Memacs._parser_parse_args(self)

        if not self._args.list_folders and not self._args.folder_name:
            self._parser.error("please specify a folder " + \
                                   "use --list to find a folder")

    def __fetch_mails_and_write(self, server, message_ids, folder_name):
        """
        Fetches All headers, let Mailparser parse each mail,
        write to outputfile

        @param server: imaplib IMAP4_SLL object
        @param message_ids: list of ids to fetch
        @param folder_name: folder name of connection
        """
        num = ",".join(message_ids)

        logging.debug(num)
        typ, data = server.uid("fetch",
                               num,
                               "(BODY.PEEK[HEADER.FIELDS " + \
                                   "(Date Subject " + \
                                   "From To Cc Reply-To Message-ID)])")

        if typ == "OK":
            i = 0

            # we have to go in step 2 because every second string is a ")"
            for i in range(0, len(data), 2):
                message = data[i][1]
                timestamp, output, note, properties = \
                    MailParser.parse_message(message)

                # just for debbuging in orgfile
                # properties.add("NUM",data[i][0][:5])
                self._writer.write_org_subitem(timestamp,
                                               output,
                                               note,
                                               properties)

        else:
            logging.error("Could not fetch mails typ - %s", typ)
            server.logout(1)
            sys.exit(1)

    def __handle_folder(self, server, folder_name):
        """
        Selects the folder, gets all ids, and calls
        self.__fetch_mails_and_write(...)

        @param server: imaplib IMAP4_SLL object
        @param folder_name: folder to select
        """
        logging.debug("folder: %s", folder_name)

        # selecting the folder
        typ, data = server.select(folder_name)
        if typ != "OK":
            logging.error("could not select folder %s", folder_name)
            server.logout()
            sys.exit(1)

        # getting all
        typ, data = server.uid('search', None, 'ALL')
        if typ == "OK":
            message_ids = data[0].split()
            logging.debug("message_ids:%s", ",".join(message_ids))

            # if number_entries is set we have to adapt messages_ids
            if self._args.number_entries:
                if len(message_ids) > self._args.number_entries:
                    message_ids = message_ids[-self._args.number_entries:]

            self.__fetch_mails_and_write(server, message_ids, folder_name)
        else:
            logging.error("Could not select folder %s - typ:%s",
                          folder_name, typ)
            server.logout()
            sys.exit(1)

    def __list_folders(self, server):
        """
        lists all folders and writes them to
        logging.info

        @param server: imaplib IMAP4_SSL object
        """
        typ, folder_list = server.list()
        if typ == "OK":
            logging.info("Folders:")
            for f in folder_list:
                logging.info(f[f.find("\"/\" \"") + 4:])
        else:
            logging.error("list folders was not ok: %s", typ)
            server.logout()
            sys.exit(1)

    def __login_server(self, server, username, password):
        """
        logs in to server, if failure then exit
        @param server: imaplib IMAP4_SSL object
        @param username
        @param password
        """
        try:
            typ, dat = server.login(username, password)
            if typ != "OK":
                logging.warning("Could not log in")
                server.logout()
                sys.exit(1)
        except Exception, e:
            if "Invalid credentials" in e[0]:
                logging.error("Invalid credentials cannot login")
                server.logout()
                sys.exit(1)
            else:
                logging.warning("Could not log in")
                server.logout()
                sys.exit(1)

    def _main(self):
        """
        get's automatically called from Memacs class
        """
        username = self._get_config_option("user")
        password = self._get_config_option("password")
        host = self._get_config_option("host")
        port = self._get_config_option("port")

        try:
            server = imaplib.IMAP4_SSL(host, int(port))
        except Exception, e:
            logging.warning("could not connect to server %s", host)
            sys.exit(1)

        self.__login_server(server, username, password)

        if self._args.list_folders == True:
            self.__list_folders(server)
        else:
            self.__handle_folder(server, self._args.folder_name)

        server.logout()

########NEW FILE########
__FILENAME__ = argparser
# -*- coding: utf-8 -*-
# Time-stamp: <2014-01-28 16:17:20 vk>

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import os
import re

class MemacsArgumentParser(ArgumentParser):
    """
    Inherited from Argumentparser

    MemacsArgumentParser handles default arguments which are needed for every
    Memacs module and gives a nicer output for help message.
    """

    def __init__(self,
                 prog_version,
                 prog_version_date,
                 prog_description,
                 copyright_year,
                 copyright_authors,
                 use_config_parser_name=""
                 ):

        self.__version = "%(prog)s v" + prog_version + " from " + \
            prog_version_date

        # format copyright authors:
        # indent from second author
        copyright_authors = copyright_authors.splitlines()
        for i in range(len(copyright_authors)):
            copyright_authors[i] = "            " + copyright_authors[i]
        copyright_authors = "\n".join(map(unicode, copyright_authors))

        epilog = ":copyright: (c) " + copyright_year + " by \n" + \
        copyright_authors + \
        "\n:license: GPL v2 or any later version\n" + \
        ":bugreports: https://github.com/novoid/Memacs\n" + \
        ":version: " + prog_version + " from " + prog_version_date + "\n"

        self.__use_config_parser_name = use_config_parser_name

        ArgumentParser.__init__(self,
                              description=prog_description,
                              add_help=True,
                              epilog=epilog,
                              formatter_class=RawDescriptionHelpFormatter
                              )
        self.__add_arguments()

    def __add_arguments(self):
        """
        Add's all standard arguments of a Memacs module
        """
        self.add_argument('--version',
                          action='version',
                          version=self.__version)

        self.add_argument("-v", "--verbose",
                          dest="verbose",
                          action="store_true",
                          help="enable verbose mode")

        self.add_argument("-s", "--suppress-messages",
                          dest="suppressmessages",
                          action="store_true",
                          help="do not show any log message " + \
                              "- helpful when -o not set")

        self.add_argument("-o", "--output",
                          dest="outputfile",
                          help="Org-mode file that will be generated " + \
                              " (see above). If no output file is given, " + \
                              "result gets printed to stdout",
                          metavar="FILE")

        self.add_argument("-a", "--append",
                          dest="append",
                          help="""when set and outputfile exists, then
                          only new entries are appendend.
                          criterion: :ID: property""",
                          action="store_true")

        self.add_argument("-t", "--tag",
                          dest="tag",
                          help="overriding tag: :Memacs:<tag>: (on top entry)")

        self.add_argument("--autotagfile",
                          dest="autotagfile",
                          help="file containing autotag information, see " + \
                          "doc file FAQs_and_Best_Practices.org",
                          metavar="FILE")

        self.add_argument("--number-entries",
                          dest="number_entries",
                          help="how many entries should be written?",
                          type=int)

        self.add_argument("--columns-header",
                          dest="columns_header",
                          help="if you want to add an #+COLUMNS header, please specify " + \
                          "its content as STRING",
                          metavar="STRING")

        self.add_argument("--custom-header",
                          dest="custom_header",
                          help="if you want to add an arbitrary header line, please specify " + \
                          "its content as STRING",
                          metavar="STRING")

        self.add_argument("--add-to-time-stamps",
                          dest="timestamp_delta",
                          help="if data is off by, e.g., two hours, you can specify \"+2\" " + \
                              "or \"-2\" here to correct it with plus/minus two hours",
                          metavar="STRING")

        self.add_argument("--inactive-time-stamps",
                          dest="inactive_timestamps",
                          help="""inactive time-stamps are written to the output file 
                          instead of active time-stamps. Helps to move modules with many entries
                          to the inactive layer of the agenda.""",
                          action="store_true")

        # ---------------------
        # Config parser
        # ---------------------
        if self.__use_config_parser_name != "":
            self.add_argument("-c", "--config",
                              dest="configfile",
                              help="path to config file",
                              metavar="FILE")

    def parse_args(self, args=None, namespace=None):
        """
        overwriting ArgParser's parse_args and
        do checking default argument outputfile
        """
        args = ArgumentParser.parse_args(self, args=args, namespace=namespace)
        if args.outputfile:
            if not os.path.exists(os.path.dirname(args.outputfile)):
                self.error("Output file path(%s) does not exist!" %
                           args.outputfile)
            if not os.access(os.path.dirname(args.outputfile), os.W_OK):
                self.error("Output file %s is not writeable!" %
                           args.outputfile)
        else:
            if args.append:
                self.error("cannot set append when no outputfile specified")

        if args.suppressmessages == True and args.verbose == True:
            self.error("cannot set both verbose and suppress-messages")

        if args.autotagfile:
            if not os.path.exists(os.path.dirname(args.autotagfile)):
                self.error("Autotag file path(%s) doest not exist!" %
                           args.autotagfile)
            if not os.access(args.autotagfile, os.R_OK):
                self.error("Autotag file (%s) is not readable!" %
                           args.autotagfile)

        if args.timestamp_delta:
            timestamp_components = re.match('[+-]\d\d?', args.timestamp_delta)
            if not timestamp_components:
                self.error("format of \"--add-to-time-stamps\" is not recognized. Should be similar " + \
                           "to ,e.g., \"+1\" or \"-3\".")

        # ---------------------
        # Config parser
        # ---------------------
        if self.__use_config_parser_name != "":
            if args.configfile:
                if not os.path.exists(args.configfile):
                    self.error("Config file (%s) does not exist" %
                        args.configfile)
                if not os.access(args.configfile, os.R_OK):
                    self.error("Config file (%s) is not readable!" %
                        args.configfile)
            else:
                self.error("please specify a config file")
        return args

########NEW FILE########
__FILENAME__ = loggingsettings
# -*- coding: utf-8 -*-
# Time-stamp: <2012-05-30 18:19:27 armin>

import logging
import sys
import os


def handle_logging(args,
                   verbose=False,
                   suppressmessages=False,
                   org_file=""):
    """
    Handle/format logging regarding boolean parameter verbose
    @param verbose: options from OptionParser
    """
    if suppressmessages == True:
        logging.basicConfig(level=logging.ERROR)
    elif verbose:
        FORMAT = "%(levelname)-8s %(asctime)-15s %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    else:
        FORMAT = "%(message)s"
        logging.basicConfig(level=logging.INFO, format=FORMAT)

    if org_file:
        if not os.path.exists(os.path.dirname(org_file)):
            org_file = None
        else:
            org_error_file = os.path.dirname(org_file) + os.sep + \
                "error.org"
            memacs_module_filename = os.path.basename(sys.argv[0])
            # add file logger
            console = logging.FileHandler(org_error_file, 'a', 'utf-8', 0)
            console.setLevel(logging.ERROR)
            formatter = logging.Formatter(
                '** %(asctime)s ' + memacs_module_filename + \
                    ' had an %(levelname)s \n   %(message)s \n' + \
                '   Arguments: ' + str(args) + '\n',
                datefmt="<%Y-%m-%d %a %H:%M:%S +1d>")
            console.setFormatter(formatter)
            logging.getLogger('').addHandler(console)

########NEW FILE########
__FILENAME__ = mailparser
# -*- coding: utf-8 -*-
# Time-stamp: <2012-03-28 20:12:09 armin>

import time
import logging
from email import message_from_string
from email.utils import parsedate
from orgproperty import OrgProperties
from orgformat import OrgFormat


class MailParser(object):

    @staticmethod
    def get_value_or_empty_str(headers, key, remove_newline=False):
        """
        @param return: headers[key] if exist else ""
        """
        ret = ""
        if key in headers:
            ret = headers[key]
            if remove_newline:
                ret = ret.replace("\n", "")
        return ret

    @staticmethod
    def parse_message(message, add_body=False):
        """
        parses whole mail from string

        @param message: mail message
        @param add_body: if specified, body is added
        @return values for OrgWriter.write_org_subitem
        """

        msg = message_from_string(message)

        # Read only these fields
        use_headers = ["To",
                       "Date",
                       "From",
                       "Subject",
                       "Reply-To",
                       "Newsgroups",
                       "Cc",
                       ]
        # These fields are added, if found to :PROPERTIES: drawer
        not_properties = ["Date",
                          "Subject",
                          "From"
                          ]

        properties = OrgProperties()
        headers = {}

        logging.debug("Message items:")
        logging.debug(msg.items())

        msg_id = None

        # fill headers and properties
        for key, value in msg.items():
            value = value.replace("\r", "").decode('utf-8')
            if key in use_headers:
                headers[key] = value
                if key not in not_properties:
                    properties.add(key, value.replace("\n", ""))

            if key.upper() == "MESSAGE-ID":
                msg_id = value

        notes = ""
        # look for payload
        # if more than one payload, use text/plain payload
        if add_body:
            payload = msg.get_payload()
            if payload.__class__ == list:
                # default use payload[0]
                payload_msg = payload[0].get_payload()
                for payload_id in len(payload):
                    for param in payload[payload_id].get_params():
                        if param[0] == 'text/plain':
                            payload_msg = payload[payload_id].get_payload()
                            break
                    if payload_msg != payload[0].get_payload():
                        break
                notes = payload_msg
            else:
                notes = payload

        notes = notes.replace("\r", "").decode('utf-8')
        output_from = MailParser.get_value_or_empty_str(headers, "From")
        if output_from != "":
            output_from = OrgFormat.contact_mail_mailto_link(output_from)
        subject = MailParser.get_value_or_empty_str(headers, "Subject", True)

        dt = MailParser.get_value_or_empty_str(headers, "Date", False)
        timestamp = ""
        if dt != "":
            try:
                time_tupel = time.localtime(time.mktime(parsedate(dt)))
                timestamp = OrgFormat.datetime(time_tupel)
            except TypeError:
                logging.error("could not parse dateime from msg %s", dt)

        properties.add_data_for_hashing(timestamp + "_" + msg_id)

        if "Newsgroups" in headers:
            ng_list = []
            for ng in headers["Newsgroups"].split(","):
                ng_list.append(OrgFormat.newsgroup_link(ng))
            output_ng = ", ".join(map(str, ng_list))
            output = output_from + u"@" + output_ng + ": " + subject
        else:
            output = output_from + u": " + subject

        return timestamp, output, notes, properties

########NEW FILE########
__FILENAME__ = memacs
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2014-01-28 16:19:18 vk>

import logging
import traceback
from argparser import MemacsArgumentParser
from orgwriter import OrgOutputWriter
from loggingsettings import handle_logging
import sys
from ConfigParser import ConfigParser


class Memacs(object):
    """
    Memacs class

    With this class it is easier to make a Memacs module
    because it handles common things like
    * default arguments + parsing
        - orgoutputfile
        - version
        - verbose
        - suppress-messages
    * set logging information
        - write error logs to error.org if
          orgfile is specified

    use handle_main() to start Memacs

    Testing:
    * use test_get_all()     for getting whole org output
    * use test_get_entries() for getting only org entries
    """

    def __init__(self,
                 prog_version="no version specified",
                 prog_version_date="no date specified",
                 prog_description="no description specified",
                 prog_short_description="no short-description specified",
                 prog_tag="no tag specified",
                 copyright_year="",
                 copyright_authors="",
                 use_config_parser_name="",
                 argv=sys.argv[1:]):
        """
        Ctor

        Please set Memacs information like version, description, ...

        set argv when you want to test class

        set write_footer i

        """
        self.__prog_version = prog_version
        self.__prog_version_date = prog_version_date
        self.__prog_description = prog_description
        self.__prog_short_description = prog_short_description
        self.__prog_tag = prog_tag
        self.__writer_append = False
        self.__copyright_year = copyright_year
        self.__copyright_authors = copyright_authors
        self.__use_config_parser_name = use_config_parser_name
        self.__config_parser = None
        self.__argv = argv

    def __init(self, test=False):
        """
        we use this method to initialize because here it could be, that
        Exceptions are thrown. in __init__() we could not catch them
        see handle_main() to understand

        @param test: used in test_get_all
        """
        self._parser = MemacsArgumentParser(
            prog_version=self.__prog_version,
            prog_version_date=self.__prog_version_date,
            prog_description=self.__prog_description,
            copyright_year=self.__copyright_year,
            copyright_authors=self.__copyright_authors,
            use_config_parser_name=self.__use_config_parser_name)
        # adding additional arguments from our subcass
        self._parser_add_arguments()
        # parse all arguments
        self._parser_parse_args()
        # set logging configuration
        handle_logging(self._args.__dict__,
                       self._args.verbose,
                       self._args.suppressmessages,
                       self._args.outputfile,
                       )

        # for testing purposes it's good to see which args are secified
        logging.debug("args specified:")
        logging.debug(self._args)

        # if an tag is specified as argument take that tag
        if self._args.tag:
            tag = self._args.tag
        else:
            tag = self.__prog_tag

        #
        if self.__use_config_parser_name != "":
            self.__config_parser = ConfigParser()
            self.__config_parser.read(self._args.configfile)
            logging.debug("cfg: %s",
                          self.__config_parser.items(
                                        self.__use_config_parser_name))

        # handling autotagging
        autotag_dict = self.__handle_autotagfile()

        ## collect additional header lines:
        additional_headerlines = False
        if self._args.columns_header:
            additional_headerlines = '#+COLUMNS: ' + self._args.columns_header
        if self._args.custom_header:
            additional_headerlines = self._args.custom_header

        # set up orgoutputwriter
        self._writer = OrgOutputWriter(
            file_name=self._args.outputfile,
            short_description=self.__prog_short_description,
            tag=tag,
            test=test,
            append=self._args.append,
            autotag_dict=autotag_dict,
            number_entries=self._args.number_entries,
            additional_headerlines = additional_headerlines,
            timestamp_delta=self._args.timestamp_delta,
            inactive_timestamps=self._args.inactive_timestamps)


    def _get_config_option(self, option):
        """
        @return: value of the option of configfile
        """
        if self.__config_parser:
            ret = self.__config_parser.get(self.__use_config_parser_name,
                                           option)
            return ret.decode("utf-8")
        else:
            raise Exception("no config parser specified, cannot get option")

    def _main(self):
        """
        does nothing in this (super) class
        this method should be overwritten by subclass
        """
        pass

    def _parser_add_arguments(self):
        """
        does nothing in this (super) class,
        In subclass we add arguments to the parser
        """
        pass

    def _parser_parse_args(self):
        """
        Let's parse the default arguments
        In subclass we have to do additional
        parsing on (the additional) arguments
        """
        self._args = self._parser.parse_args(self.__argv)

    def __get_writer_data(self):
        """
        @return org_file_data (only when on testing)
        """
        return self._writer.get_test_result()

    def handle_main(self):
        """
        this should be called instead of main()

        With this method we can catch exceptions
        and log them as error

        logging.error makes a org-agenda-entry too if a
        outputfile was specified :)
        """
        try:
            self.__init()
            self._main()
            self._writer.close()
        except KeyboardInterrupt:
            logging.info("Received KeyboardInterrupt")
        except SystemExit, e:
            # if we get an sys.exit() do exit!
            sys.exit(e)
        except:
            error_lines = traceback.format_exc().splitlines()
            logging.error("\n   ".join(map(str, error_lines)))
            raise  # re raise exception

    def test_get_all(self):
        """
        Use this for Testing

        @param return: whole org-file
        """
        self.__init(test=True)
        self._main()
        self._writer.close()
        return self.__get_writer_data()

    def test_get_entries(self):
        """
        Use this for Testing

        @param return: org-file without header +footer (only entries)
        """
        data = self.test_get_all()
        ret_data = []
        for d in data.splitlines():
            if d[:2] != "* " and d[:1] != "#":
                ret_data.append(d)
        return ret_data

    def __handle_autotagfile(self):
        """
        read out the autotag file and generate a dict
        @return - return autotag_dict
        """
        autotag_dict = {}

        if self._args.autotagfile:
            cfgp = ConfigParser()
            cfgp.read(self._args.autotagfile)

            if "autotag" not in cfgp.sections():
                logging.error("autotag file contains no section [autotag]")
                sys.exit(1)

            for item in cfgp.items("autotag"):
                tag = item[0]
                values = item[1].split(",")
                values = map(lambda x: x.strip(), values)
                autotag_dict[tag] = values

        return autotag_dict

########NEW FILE########
__FILENAME__ = orgformat
# -*- coding: utf-8 -*-
# Time-stamp: <2014-03-13 17:13:23 karl.voit>

## This file is originally from Memacs
## https://github.com/novoid/Memacs
## and was written mainly by https://github.com/awieser
## see: https://github.com/novoid/Memacs/blob/master/memacs/lib/orgformat.py
## for unit tests, see: https://github.com/novoid/Memacs/blob/master/memacs/lib/tests/orgformat_test.py

import time
import datetime
import calendar
import logging
import re

#import pdb  ## pdb.set_trace()  ## FIXXME


class TimestampParseException(Exception):
    """
    Own excption should be raised when
    strptime fails
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class OrgFormat(object):
    """
    Class for handle special Org Formats linke link, time
    """

    SINGLE_ORGMODE_TIMESTAMP = "([<\[]([12]\d\d\d)-([012345]\d)-([012345]\d) " + \
        "(Mon|Tue|Wed|Thu|Fri|Sat|Sun) " + \
        "(([01]\d)|(20|21|22|23)):([012345]\d)[>\]])"

    ORGMODE_TIMESTAMP_REGEX = re.compile(SINGLE_ORGMODE_TIMESTAMP + "$")

    ORGMODE_TIMESTAMP_RANGE_REGEX = re.compile(SINGLE_ORGMODE_TIMESTAMP + "-(-)?" + SINGLE_ORGMODE_TIMESTAMP + "$")

    @staticmethod
    def struct_time_to_datetime(tuple_date):
        """
        returns a datetime object which was generated from the struct_time parameter
        @param struct_time with possible false day of week
        """

        assert tuple_date.__class__ == time.struct_time

        return datetime.datetime(tuple_date.tm_year,
                                 tuple_date.tm_mon,
                                 tuple_date.tm_mday,
                                 tuple_date.tm_hour,
                                 tuple_date.tm_min,
                                 tuple_date.tm_sec)

    @staticmethod
    def datetime_to_struct_time(tuple_date):
        """
        returns time.struct_time which was generated from the datetime.datetime parameter
        @param datetime object
        """

        assert tuple_date.__class__ == datetime.datetime

        return tuple_date.timetuple()

    @staticmethod
    def fix_struct_time_wday(tuple_date):
        """
        returns struct_time timestamp with correct day of week
        @param struct_time with possible false day of week
        """

        assert tuple_date.__class__ == time.struct_time

        datetimestamp = OrgFormat.struct_time_to_datetime(tuple_date)

        return time.struct_time([datetimestamp.year,
                                 datetimestamp.month,
                                 datetimestamp.day,
                                 datetimestamp.hour,
                                 datetimestamp.minute,
                                 datetimestamp.second,
                                 datetimestamp.weekday(),
                                 0, 0])

    ## timestamp = time.struct_time([2013,4,3,10,54,0,0,0,0])  ## wday == 0
    ## OrgFormat.date(timestamp)  ## '<2013-04-03 Mon>' -> Mon is wrong for April 3rd 2013
    ## OrgFormat.date( OrgFormat.fix_struct_time_wday(timestamp) ) ## '<2013-04-03 Wed>'

    @staticmethod
    def link(link, description=None, replacespaces=True):
        """
        returns string of a link in org-format
        @param link link to i.e. file
        @param description optional
        @param replacespaces: if True (default), spaces within link are being sanitized
        """

        if replacespaces:
            link = link.replace(" ", "%20")

        if description:
            return u"[[" + link + u"][" + description + u"]]"
        else:
            return u"[[" + link + u"]]"

    @staticmethod
    def date(tuple_date, show_time=False):
        """
        returns a date string in org format
        i.e.: * <YYYY-MM-DD Sun>
              * <YYYY-MM-DD Sun HH:MM>
        @param tuple_date: has to be of type time.struct_time or datetime
        @param show_time: optional show time also
        """
        # <YYYY-MM-DD hh:mm>
        assert (tuple_date.__class__ == time.struct_time or tuple_date.__class__ == datetime.datetime)

        local_structtime = False

        if tuple_date.__class__ == time.struct_time:
            ## fix day of week in struct_time
            local_structtime = OrgFormat.fix_struct_time_wday(tuple_date)
        else:
            ## convert datetime to struc_time
            local_structtime = OrgFormat.datetime_to_struct_time(tuple_date)

        if show_time:
            return time.strftime("<%Y-%m-%d %a %H:%M>", local_structtime)
        else:
            return time.strftime("<%Y-%m-%d %a>", local_structtime)

    @staticmethod
    def inactive_date(tuple_date, show_time=False):
        """
        returns a date string in org format
        i.e.: * [YYYY-MM-DD Sun]
              * [YYYY-MM-DD Sun HH:MM]
        @param tuple_date: has to be a time.struct_time
        @param show_time: optional show time also
        """
        # <YYYY-MM-DD hh:mm>
        assert tuple_date.__class__ == time.struct_time

        if show_time:
            return time.strftime("[%Y-%m-%d %a %H:%M]", OrgFormat.fix_struct_time_wday(tuple_date))
        else:
            return time.strftime("[%Y-%m-%d %a]", OrgFormat.fix_struct_time_wday(tuple_date))

    @staticmethod
    def datetime(tuple_datetime):
        """
        returns a date+time string in org format
        wrapper for OrgFormat.date(show_time=True)

        @param tuple_datetime has to be a time.struct_time
        """
        return OrgFormat.date(tuple_datetime, show_time=True)

    @staticmethod
    def inactive_datetime(tuple_datetime):
        """
        returns a date+time string in org format
        wrapper for OrgFormat.inactive_date(show_time=True)

        @param tuple_datetime has to be a time.struct_time
        """
        return OrgFormat.inactive_date(tuple_datetime, show_time=True)

    @staticmethod
    def daterange(begin, end):
        """
        returns a date range string in org format

        @param begin,end: has to be a time.struct_time
        """
        assert type(begin) == time.struct_time
        assert type(end) == time.struct_time
        return "%s--%s" % (OrgFormat.date(begin, False),
                           OrgFormat.date(end, False))

    @staticmethod
    def datetimerange(begin, end):
        """
        returns a date range string in org format

        @param begin,end: has to be a time.struct_time
        """
        assert type(begin) == time.struct_time
        assert type(end) == time.struct_time
        return "%s--%s" % (OrgFormat.date(begin, True),
                           OrgFormat.date(end, True))

    @staticmethod
    def utcrange(begin_tupel, end_tupel):
        """
        returns a date(time) range string in org format
        if both parameters do not contain time information,
        utcrange is same as daterange, else it is same as datetimerange.

        @param begin,end: has to be a a time.struct_time
        """

        if begin_tupel.tm_sec == 0 and \
                begin_tupel.tm_min == 0 and \
                begin_tupel.tm_hour == 0 and \
                end_tupel.tm_sec == 0 and \
                end_tupel.tm_min == 0 and \
                end_tupel.tm_hour == 0:

            return OrgFormat.daterange(begin_tupel, end_tupel)
        else:
            return OrgFormat.datetimerange(begin_tupel, end_tupel)

    @staticmethod
    def strdate(date_string, inactive=False):
        """
        returns a date string in org format
        i.e.: * <YYYY-MM-DD Sun>
        @param date-string: has to be a str in following format:  YYYY-MM-DD
        @param inactive: (boolean) True: use inactive time-stamp; else use active
        """
        assert date_string.__class__ == str or date_string.__class__ == unicode
        tuple_date = OrgFormat.datetupeliso8601(date_string)
        if inactive:
            return OrgFormat.inactive_date(tuple_date, show_time=False)
        else:
            return OrgFormat.date(tuple_date, show_time=False)

    @staticmethod
    def strdatetime(datetime_string):
        """
        returns a date string in org format
        i.e.: * <YYYY-MM-DD Sun HH:MM>
        @param date-string: has to be a str in
                           following format: YYYY-MM-DD HH:MM
        """
        assert datetime_string.__class__ == str or \
            datetime_string.__class__ == unicode
        try:
            tuple_date = time.strptime(datetime_string, "%Y-%m-%d %H:%M")
        except ValueError, e:
            raise TimestampParseException(e)
        return OrgFormat.date(tuple_date, show_time=True)

    @staticmethod
    def strdatetimeiso8601(datetime_string):
        """
        returns a date string in org format
        i.e.: * <YYYY-MM-DD Sun HH:MM>
        @param date-string: has to be a str
                            in following format: YYYY-MM-DDTHH.MM.SS or
                                                 YYYY-MM-DDTHH.MM
        """
        assert datetime_string.__class__ == str or \
            datetime_string.__class__ == unicode
        tuple_date = OrgFormat.datetimetupeliso8601(datetime_string)
        return OrgFormat.date(tuple_date, show_time=True)

    @staticmethod
    def datetimetupeliso8601(datetime_string):
        """
        returns a time_tupel
        @param datetime_string: YYYY-MM-DDTHH.MM.SS or
                                YYYY-MM-DDTHH.MM
        """
        assert datetime_string.__class__ == str or \
            datetime_string.__class__ == unicode
        try:
            if len(datetime_string) == 16:  # YYYY-MM-DDTHH.MM
                return time.strptime(datetime_string, "%Y-%m-%dT%H.%M")
            elif len(datetime_string) == 19:  # YYYY-MM-DDTHH.MM.SS
                return time.strptime(datetime_string, "%Y-%m-%dT%H.%M.%S")
        except ValueError, e:
            raise TimestampParseException(e)

    @staticmethod
    def datetupeliso8601(datetime_string):
        """
        returns a time_tupel
        @param datetime_string: YYYY-MM-DD
        """
        assert datetime_string.__class__ == str or \
            datetime_string.__class__ == unicode
        try:
            return time.strptime(datetime_string, "%Y-%m-%d")
        except ValueError, e:
            raise TimestampParseException(e)

    @staticmethod
    def datetupelutctimestamp(datetime_string):
        """
        returns a time_tupel
        @param datetime_string: YYYYMMDDTHHMMSSZ or
                                YYYYMMDDTHHMMSS or
                                YYYYMMDD
        """
        assert datetime_string.__class__ == str or \
            datetime_string.__class__ == unicode
        string_length = len(datetime_string)

        try:
            if string_length == 16:
                #YYYYMMDDTHHMMSSZ
                return time.localtime(
                    calendar.timegm(
                        time.strptime(datetime_string, "%Y%m%dT%H%M%SZ")))
            elif string_length == 15:
                #YYYYMMDDTHHMMSS
                return time.strptime(datetime_string, "%Y%m%dT%H%M%S")
            elif string_length == 8:
                #YYYYMMDD
                return time.strptime(datetime_string, "%Y%m%d")
            elif string_length == 27:
                #2011-11-02T14:48:54.908371Z
                datetime_string = datetime_string.split(".")[0] + "Z"
                return time.localtime(
                    calendar.timegm(
                        time.strptime(datetime_string,
                                      "%Y-%m-%dT%H:%M:%SZ")))
            else:
                logging.error("string has no correct format: %s",
                              datetime_string)
        except ValueError, e:
            raise TimestampParseException(e)

    # @staticmethod
    # def date_tupel_mail_date(mail_date_string):
    #     """
    #     @param mail_date_string: following format:
    #         "Mon, 26 Dec 2011 17:16:28 +0100"
    #     @return: time_struct
    #     """
    #
    #     return None

    @staticmethod
    def contact_mail_mailto_link(contact_mail_string):
        """
        @param contact_mailto_string: possibilities:
        - "Bob Bobby <bob.bobby@example.com>" or
        - <Bob@example.com>"

        @return:
        - [[mailto:bob.bobby@example.com][Bob Bobby]]
        - [[mailto:bob.bobby@example.com][bob.bobby@excample.com]]
        """
        delimiter = contact_mail_string.find("<")
        name = contact_mail_string[:delimiter].strip()
        mail = contact_mail_string[delimiter + 1:][:-1].strip()
        if name != "":
            return u"[[mailto:" + mail + u"][" + name + u"]]"
        else:
            return u"[[mailto:" + mail + u"][" + mail + u"]]"

    @staticmethod
    def newsgroup_link(newsgroup_string):
        """
        @param newsgroup_string: Usenet name
            i.e: news:comp.emacs
        @param return: [[news:comp.emacs][comp.emacs]]
        """
        return "[[news:" + newsgroup_string + "][" + newsgroup_string + "]]"

    @staticmethod
    def get_hms_from_sec(sec):
        """
        Returns a string of hours:minutes:seconds from the seconds given.

        @param sec: seconds
        @param return: h:mm:ss as string
        """

        assert sec.__class__ == int

        seconds = sec % 60
        minutes = (sec / 60) % 60
        hours = (sec / (60 * 60))

        return str(hours) + ":" + str(minutes).zfill(2) + ":" + str(seconds).zfill(2)

    @staticmethod
    def get_dhms_from_sec(sec):
        """
        Returns a string of days hours:minutes:seconds (like
        "9d 13:59:59") from the seconds given. If days is zero, omit
        the part of the days (like "13:59:59").

        @param sec: seconds
        @param return: xd h:mm:ss as string
        """

        assert sec.__class__ == int

        seconds = sec % 60
        minutes = (sec / 60) % 60
        hours = (sec / (60 * 60)) % 24
        days = (sec / (60 * 60 * 24))

        if days > 0:
            daystring = str(days) + "d "
        else:
            daystring = ''

        return daystring + str(hours) + ":" + str(minutes).zfill(2) + ":" + str(seconds).zfill(2)

    @staticmethod
    def orgmode_timestamp_to_datetime(orgtime):
        """
        Returns a datetime object containing the time-stamp of an Org-mode time-stamp.

        @param orgtime: <YYYY-MM-DD Sun HH:MM>
        @param return: date time object
        """

        assert orgtime.__class__ == str or \
            orgtime.__class__ == unicode

        components = re.match(OrgFormat.ORGMODE_TIMESTAMP_REGEX, orgtime)

        assert components

        ## components: <1980-12-31 Wed 23:59>
        ## components.groups(1) -> ('1980', '12', '31', 'Wed', '23', 1, '23', '59')

        year = int(components.group(2))
        month = int(components.group(3))
        day = int(components.group(4))
        hour = int(components.group(6))
        minute = int(components.group(9))

        return datetime.datetime(year, month, day, hour, minute, 0)

    @staticmethod
    def apply_timedelta_to_Orgmode_timestamp(orgtime, deltahours):
        """
        Returns a string containing an Org-mode time-stamp which has
        delta added in hours. It works also for a time-stamp range
        which uses two strings <YYYY-MM-DD Sun HH:MM> concatenated
        with one or two dashes.

        @param orgtime: <YYYY-MM-DD Sun HH:MM>
        @param deltahours: integer like, e.g., "3" or "-2" (in hours)
        @param return: <YYYY-MM-DD Sun HH:MM>
        """

        assert deltahours.__class__ == int
        assert orgtime.__class__ == str or \
            orgtime.__class__ == unicode

        ## first time-stamp: range_components.groups(0)[0]
        ## second time-stamp: range_components.groups(0)[10]
        range_components = re.match(OrgFormat.ORGMODE_TIMESTAMP_RANGE_REGEX, orgtime)

        if range_components:
            return OrgFormat.datetime(
                OrgFormat.orgmode_timestamp_to_datetime(
                    range_components.groups(0)[0]) +
                datetime.timedelta(0, 0, 0, 0, 0, deltahours)) + \
                "-" + \
                OrgFormat.datetime(
                    OrgFormat.orgmode_timestamp_to_datetime(
                        range_components.groups(0)[10]) +
                    datetime.timedelta(0, 0, 0, 0, 0, deltahours))
        else:
            return OrgFormat.datetime(OrgFormat.orgmode_timestamp_to_datetime(orgtime) +
                                      datetime.timedelta(0, 0, 0, 0, 0, deltahours))


# Local Variables:
# mode: flyspell
# eval: (ispell-change-dictionary "en_US")
# End:

########NEW FILE########
__FILENAME__ = orgproperty
# -*- coding: utf-8 -*-
# Time-stamp: <2012-09-06 22:07:05 armin>
import hashlib


class OrgProperties(object):
    """
    Class for handling Memacs's org-drawer:

    :PROPERTIES:
    ...
    :<tag>: value
    ...
    :ID:  - id is generated from all above tags/values
    :END:
    """

    def __init__(self, data_for_hashing=""):
        """
        Ctor
        @param data_for_hashing: if no special properties are set,
        you can add here data only for hash generation
        """
        self.__properties = {}
        self.__properties_multiline = {}
        self.__data_for_hashing = data_for_hashing
        self.__id = None

    def add(self, tag, value):
        """
        Add an OrgProperty(tag,value) to the properties
        @param tag: property tag
        @param value: property value
        """
        tag = unicode(tag).strip().upper()
        value = unicode(value).strip()

        if tag == "ID":
            raise Exception("you should not specify an :ID: property " + \
                            "it will be generated automatically")

        value_multiline = value.splitlines()

        if len(value_multiline) > 1:
            # we do have multiline value
            multiline_value = ["   " + v for v in value_multiline]
            self.__properties_multiline[tag] = multiline_value

            value = " ".join(value_multiline)

        self.__properties[tag] = unicode(value)

    def set_id(self, value):
        """
        set id here, then its not generated / hashed
        """
        self.__id = value

    def delete(self, key):
        """
        delete a pair out of properties
        @param key index
        """
        try:
            del self.__properties[key]
            del self.__properties_multiline[key]
        except Keyerror, e:
            pass

    def __get_property_max_tag_width(self):
        width = 10  # :PROPERTIES: has width 10
        for key in self.__properties.keys():
            if width < len(key):
                width = len(key)
        return width

    def __format_tag(self, tag):
        num_whitespaces = self.__get_property_max_tag_width() - len(tag)
        whitespaces = ""
        for w in range(num_whitespaces):
            whitespaces += " "
        return "   :" + tag + ": " + whitespaces

    def __unicode__(self):
        """
        for representig properties in unicode with org formatting
        """

        if self.__properties == {} and \
            self.__data_for_hashing == "" and \
            self.__id == None:
            raise Exception("No data for hashing specified,  and no " + \
                            "property was given. Cannot generate unique ID.")

        ret = "   :PROPERTIES:\n"

        for tag, value in self.__properties.iteritems():
            ret += self.__format_tag(tag) + value + "\n"

        ret += self.__format_tag("ID") + self.get_id() + "\n"
        ret += "   :END:"
        return ret

    def get_id(self):
        """
        generates the hash string for all properties
        @return: sha1(properties)
        """
        if self.__id != None:
            return self.__id
        to_hash = "".join(map(unicode, self.__properties.values()))
        to_hash += "".join(map(unicode, self.__properties.keys()))
        to_hash += self.__data_for_hashing
        return hashlib.sha1(to_hash.encode('utf-8')).hexdigest()

    def get_value(self, key):
        """
        @param: key of property
        @return: returns the value of a given key
        """
        return self.__properties[key]

    def add_data_for_hashing(self, data_for_hashing):
        """
        add additional data for hashing
        useful when no possibility to set in Ctor
        """
        self.__data_for_hashing += data_for_hashing

    def get_value_delete_but_add_for_hashing(self, key):
        """
        see method name ;)
        """
        ret = self.get_value(key)
        self.delete(key)
        self.add_data_for_hashing(ret)
        return ret

    def get_multiline_properties(self):
        ret = ""
        for key in self.__properties_multiline.keys():
            ret += "\n   " + key + ":\n"
            ret += "\n".join(self.__properties_multiline[key])
            ret += "\n"

        return ret

########NEW FILE########
__FILENAME__ = orgwriter
# -*- coding: utf-8 -*-
# Time-stamp: <2013-12-15 16:48:39 vk>

import codecs
import sys
import time
import os
import re
import logging
from orgproperty import OrgProperties
from reader import CommonReader
from orgformat import OrgFormat


class OrgOutputWriter(object):
    """
    OrgOutputWriter is used especially for writing
    org-mode entries

    most notable function:
    - write_org_subitem (see its comment)
    """
    __handler = None
    __test = False

    def __init__(self,
                 short_description,
                 tag,
                 file_name=None,
                 test=False,
                 append=False,
                 autotag_dict={},
                 number_entries=None,
                 additional_headerlines=None,
                 timestamp_delta=None,
                 inactive_timestamps=False):
        """
        @param file_name:
        """
        self.__test = test
        self.__test_data = ""
        self.__append = append
        self.__time = time.time()
        self.__short_description = short_description
        self.__tag = tag
        self.__file_name = file_name
        self.__existing_ids = []
        self.__autotag_dict = autotag_dict
        self.__number_entries = number_entries
        self.__entries_count = 0
        self.__lower_autotag_dict()
        self.__additional_header_lines = additional_headerlines
        self.__timestamp_delta = timestamp_delta
        self.__inactive_timestamps = inactive_timestamps

        if self.__timestamp_delta is not None:
            logging.debug("orgwriter: timestamp_delta found: %s" , timestamp_delta)

        if file_name:
            if append and os.path.exists(file_name):
                self.__handler = codecs.open(file_name, 'a', u"utf-8")
                self.__compute_existing_id_list()
            else:
                self.__handler = codecs.open(file_name, 'w', u"utf-8")
                self.__write_header()
        else:
            self.__write_header()

    def get_test_result(self):
        return self.__test_data

    def write(self, output):
        """
        Write "<output>"
        """
        if self.__handler:
            self.__handler.write(unicode(output))
        else:
            if self.__test:
                self.__test_data += output
            else:
                # don't remove the comma(otherwise there will be a \n)
                print output,

    def writeln(self, output=""):
        """
        Write "<output>\n"
        """
        self.write(unicode(output) + u"\n")

    def __write_header(self):
        """
        Writes the header of the file

        __init__() does call this function
        """
        self.write_commentln(u"-*- coding: utf-8 mode: org -*-")
        self.write_commentln(
            u"this file is generated by " + sys.argv[0] + \
                ". Any modification will be overwritten upon next invocation!")
        self.write_commentln(
            "To add this file to your org-agenda files open the stub file " + \
                " (file.org) not this file(file.org_archive) with emacs" + \
                "and do following: M-x org-agenda-file-to-front")
        if self.__additional_header_lines:
            for line in self.__additional_header_lines.split('\n'):
                self.writeln(line)
        self.write_org_item(
            self.__short_description + "          :Memacs:" + self.__tag + ":")

    def __write_footer(self):
        """
        Writes the footer of the file including calling python script and time

        Don't call this function - call instead function close(),
        close() does call this function
        """
        self.writeln(u"* successfully parsed " +\
                     unicode(self.__entries_count) + \
                     " entries by " + \
                     sys.argv[0] + u" at " + \
                     OrgFormat.inactive_datetime(time.localtime()) + \
                     u" in ~" + self.__time + u".")

    def write_comment(self, output):
        """
        Write output as comment: "## <output>"
        """
        self.write(u"## " + output)

    def write_commentln(self, output):
        """
        Write output line as comment: "## <output>\n"
        """
        self.write_comment(output + u"\n")

    def write_org_item(self, output):
        """
        Writes an org item line.

        i.e: * <output>\n
        """
        self.writeln("* " + output)

    def __write_org_subitem(self,
                            timestamp,
                            output,
                            note="",
                            properties=OrgProperties(),
                            tags=[]):
        """
        internally called by write_org_subitem and __append_org_subitem
        """
        output_tags = ""
        if tags != []:
            output_tags = u"\t:" + ":".join(map(str, tags)) + ":"

        output = output.lstrip()
        timestamp = timestamp.strip()

        self.writeln(u"** " + timestamp + u" " + output + output_tags)
        if note != "":
            for n in note.splitlines():
                self.writeln("   " + n)
        self.writeln(unicode(properties))
        if self.__test:
            self.write(properties.get_multiline_properties())
        else:
            self.writeln(properties.get_multiline_properties())

    def write_org_subitem(self,
                          timestamp,
                          output,
                          note="",
                          properties=OrgProperties(),
                          tags=None):
        """
        Writes an org item line.

        i.e:** <timestamp> <output> :<tags>:\n
               :PROPERTIES:
               <properties>
               :ID: -generated id-
               :END:

        if an argument -a or --append is given,
        then a desicion regarding the :ID: is made if the item has to be
        written to file

        @param timestamp: str/unicode
        @param output: st tar/unicode
        @param note: str/unicode
        @param tags: list of tags
        @param properties: OrgProperties object
        """
        assert (timestamp.__class__ == str or timestamp.__class__ == unicode)
        assert tags.__class__ == list or tags == None
        assert properties.__class__ == OrgProperties
        assert (output.__class__ == str or output.__class__ == unicode)
        assert (note.__class__ == str or note.__class__ == unicode)

        # count the entries we have written, if above our limit do not write
        if self.__number_entries and \
            self.__entries_count == self.__number_entries:
            return
        else:
            self.__entries_count += 1

        if tags == None:
            tags = []

        if self.__autotag_dict != {}:
            self.__get_autotags(tags, output)

        ## fix time-stamps (if user wants to)
        if self.__timestamp_delta:
            timestamp = OrgFormat.apply_timedelta_to_Orgmode_timestamp(timestamp, int(self.__timestamp_delta))

        ## a bit of a hack to get inactive time-stamps:
        ## FIXXME: use OrgFormat method to generate inactive time-stamps in the first place and remove asserts
        if self.__inactive_timestamps:
            assert(timestamp[0] == '<')  ## at least try to find cases where this replace method fails
            assert(timestamp[-1] == '>')  ## at least try to find cases where this replace method fails
            timestamp = '[' + timestamp[1:-1] + ']'

        if self.__append:
            self.__append_org_subitem(timestamp,
                                      output,
                                      note,
                                      properties,
                                      tags)
        else:
            self.__write_org_subitem(timestamp,
                                     output,
                                     note,
                                     properties,
                                     tags)


    def __append_org_subitem(self,
                             timestamp,
                             output,
                             note="",
                             properties=OrgProperties(),
                             tags=[]):
        """
        Checks if subitem exists in orgfile (:ID: <id> is same),
        if not, it will be appended
        """
        identifier = properties.get_id()

        if id == None:
            raise Exception("id :ID: Property not set!")

        if self.__id_exists(identifier):
            # do nothing, id exists ...
            logging.debug("NOT appending")
        else:
            # id does not exist so we can append
            logging.debug("appending")
            self.__write_org_subitem(timestamp, output, note, properties, tags)

    def __compute_existing_id_list(self):
        """
        Reads the outputfile, looks for :ID: properties and stores them in
        self.__existing_ids
        """
        assert self.__existing_ids == []

        data = CommonReader.get_data_from_file(self.__file_name)

        for found_id in re.findall(":ID:(.*)\n.*:END:", data):
            found_id = found_id.strip()
            if found_id != "":
                self.__existing_ids.append(found_id)
                logging.debug("found id :ID: %s", found_id)
        logging.debug("there are already %d entries", len(self.__existing_ids))

    def __id_exists(self, searchid):
        """
        @return: if searchid already exists in output file
        """
        return unicode(searchid).strip() in self.__existing_ids

    def close(self):
        """
        Writes the footer and closes the file
        @param write_footer: write the foother with time ?
        """
        self.__time = "%1fs " % (time.time() - self.__time)
        if not self.__append:
            self.__write_footer()
        if self.__handler != None:
            self.__handler.close()

    def __lower_autotag_dict(self):
        """
        lowers all values of dict
        """
        for tag in self.__autotag_dict.iterkeys():
            values = []

            for value in self.__autotag_dict[tag]:
                values.append(value.lower())

            self.__autotag_dict[tag] = values

    def __get_autotags(self, tags, string):
        """
        Searches for tags in a given wordlist.
        Append them to tags

        @param tags: list to append the matched tags
        @param string: string to look for matching values
        """
        string = string.lower()

        for autotag_tag in self.__autotag_dict.iterkeys():
            for matching_word in self.__autotag_dict[autotag_tag]:
                if matching_word in string:
                    if autotag_tag not in tags:
                        tags.append(autotag_tag)
                    continue

########NEW FILE########
__FILENAME__ = reader
# -*- coding: utf-8 -*-
# Time-stamp: <2012-05-24 19:08:10 armin>

import codecs
import logging
import sys
import csv
from urllib2 import urlopen
from urllib2 import HTTPError
from urllib2 import URLError


class CommonReader:
    """
    Class for reading
    * files
    * url's
    """

    @staticmethod
    def get_data_from_file(path, encoding='utf-8'):
        """
        reads a file

        @param file: path to file
        @return: returns data
        """
        try:
            input_file = codecs.open(path, 'rb', encoding=encoding)
            data = input_file.read()
            input_file.close()
            return data
        except IOError, e:
            logging.error("Error at opening file: %s:%s", path, e)
            sys.exit(1)

    @staticmethod
    def get_reader_from_file(path):
        """
        gets a stream of a file
        @param path: file
        @return: stream of file
        """
        try:
            return codecs.open(path, encoding='utf-8')
        except IOError, e:
            logging.error("Error at opening file: %s:%s", path, e)
            sys.exit(1)
        return None

    @staticmethod
    def get_data_from_url(url):
        """
        reads from a url

        @param url: url to read
        @return: returns data
        """
        try:
            req = urlopen(url, None, 10)
            return req.read()
        except HTTPError, e:
            logging.error("HTTPError: %s", e)
            sys.exit(1)
        except URLError, e:
            logging.error("URLError: %s", e)
            sys.exit(1)
        except ValueError, e:
            logging.error("ValueError: %s", e)
            sys.exit(1)
        except Exception, e:
            logging.error("Exception: %s", e)
            sys.exit(1)

    @staticmethod
    def get_data_from_stdin():
        """
        reads from stdin
        @return: data from stdin
        """
        input_stream = codecs.getreader('utf-8')(sys.stdin)
        data = input_stream.read()
        input_stream.close()
        return data

    @staticmethod
    def get_reader_from_stdin():
        """
        get a utf-8 stream reader for stdin
        @return: stdin-stream
        """
        return codecs.getreader('utf-8')(sys.stdin)


class UTF8Recoder:
    """
    from http://docs.python.org/library/csv.html
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """

    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeCsvReader:
    """
    from http://docs.python.org/library/csv.html

    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, delimiter=";", encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, delimiter=delimiter, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

########NEW FILE########
__FILENAME__ = argparser_test
# -*- coding: utf-8 -*-
# Time-stamp: <2011-12-30 12:16:47 armin>

import unittest
import os
from memacs.lib.argparser import MemacsArgumentParser


class TestArgParser(unittest.TestCase):
    def setUp(self):
        self.prog_version = "0.1"
        self.prog_version_date = "2011-12-19"
        self.description = "descriptionbla"
        self.copyright_year = "2011"
        self.copyright_authors = "Armin Wieser <armin.wieser@gmail.com>"
        self.parser = MemacsArgumentParser(
            prog_version=self.prog_version,
            prog_description=self.description,
            prog_version_date=self.prog_version_date,
            copyright_authors=self.copyright_authors,
            copyright_year=self.copyright_year)
        self.TMPFOLDER = os.path.normpath(
            os.path.dirname(os.path.abspath(__file__)) + os.path.sep + \
                "tmp") + os.sep
        if not os.path.exists(self.TMPFOLDER):
            os.makedirs(self.TMPFOLDER)

    def test_verbose(self):
        """
        testing MemacsArgumentParser's argument verbose
        """
        args = self.parser.parse_args('-v'.split())
        args2 = self.parser.parse_args('--verbose'.split())

        self.assertEqual(args, args2, "-v and --verbose do different things")
        self.assertEqual(args.outputfile, None,
                         "verbose - args.outputfile should be None")
        self.assertEqual(args.suppressmessages, False,
                         "verbose - args.suppressmessages should be False")
        self.assertEqual(args.verbose, True,
                         "verbose - args.verbose should be True")

    def test_suppress(self):
        """
        testing MemacsArgumentParser's suppress-messages
        """
        args = self.parser.parse_args('-s'.split())
        args2 = self.parser.parse_args('--suppress-messages'.split())

        self.assertEqual(args, args2,
                         "-s and --suppress-messages do different things")
        self.assertEqual(args.outputfile, None,
                         "suppressmessages - args.outputfile should be None")
        self.assertEqual(
            args.suppressmessages, True,
            "suppressmessages - args.suppressmessages should be True")
        self.assertEqual(args.verbose, False,
                         "suppressmessages - args.verbose should be False")

    def test_outputfile(self):
        #args = self.parser.parse_args('-o'.split())
        outputfile_path = self.TMPFOLDER + "outputfile"
        outputfile_argument = "-o " + outputfile_path
        outputfile_argument2 = "--output " + outputfile_path
        args = self.parser.parse_args(outputfile_argument.split())
        args2 = self.parser.parse_args(outputfile_argument2.split())
        self.assertEqual(args, args2, "-o and --output do different things")

    def test_nonexistingoutputdir(self):
        outputfile_path = self.TMPFOLDER + "NONEXIST" + os.sep + "outputfile"
        outputfile_argument = "-o " + outputfile_path

        try:
            self.parser.parse_args(outputfile_argument.split())
            self.assertTrue(False,
                            "parsing was correct altough nonexist. outputfile")
        except SystemExit:
            pass

    def test_verbose_suppress_both(self):
        try:
            self.parser.parse_args('-s -v'.split())
            self.assertTrue(
                False,
                "parsing was correct altough " + \
                    "both suppress and verbose was specified")
        except SystemExit:
            pass

########NEW FILE########
__FILENAME__ = mailparser_test
# -*- coding: utf-8 -*-
# Time-stamp: <2011-12-30 12:16:47 armin>

import unittest
from memacs.lib.mailparser import MailParser


class TestMailParser(unittest.TestCase):

    def test_parse_mail_without_body(self):
        message = """Date: Wed, 28 Dec 2011 14:02:00 +0100
From: Alice Ally <alice@ally.com>
To: Bob Bobby <Bob@bobby.com>
Subject: Bob sends a mesage
Message-ID: f2c1165a321d0e0@foo.com
X-Scanned-By: MIMEDefang 2.71 on 129.27.10.2

Hi!

Hope you can read my message

kind reagards,
Bob
        """
        timestamp, output, notes, properties = \
            MailParser.parse_message(message)

        self.assertEqual(timestamp, "<2011-12-28 Wed 14:02>")
        self.assertEqual(output, "[[mailto:alice@ally.com]" + \
                         "[Alice Ally]]: Bob sends a mesage")
        self.assertEqual(notes, "")
        p = """   :PROPERTIES:
   :TO:         Bob Bobby <Bob@bobby.com>
   :ID:         8fd560c32d51c455744df7abd26ea545924ba632
   :END:"""

        self.assertEqual(unicode(properties), p)

    def test_parse_mail_with_body(self):
        message = """Date: Wed, 28 Dec 2011 14:02:00 +0100
From: Alice Ally <alice@ally.com>
To: Bob Bobby <Bob@bobby.com>
Subject: Bob sends a mesage
Message-ID: f2c1165a321d0e0@foo.com
X-Scanned-By: MIMEDefang 2.71 on 129.27.10.2

Hi!

Hope you can read my message

kind reagards,
Bob"""
        timestamp, output, notes, properties = \
            MailParser.parse_message(message,
                                     True)

        self.assertEqual(timestamp, "<2011-12-28 Wed 14:02>")
        self.assertEqual(output, "[[mailto:alice@ally.com]" + \
                         "[Alice Ally]]: Bob sends a mesage")
        self.assertEqual(notes, "Hi!\n\nHope you can read my message\n" + \
                            "\nkind reagards,\nBob")
        p = """   :PROPERTIES:
   :TO:         Bob Bobby <Bob@bobby.com>
   :ID:         8fd560c32d51c455744df7abd26ea545924ba632
   :END:"""

        self.assertEqual(unicode(properties), p)

    def test_parse_ng_with_body(self):
        message = """Path: news.tugraz.at!not-for-mail
From: Alice Ally <alice@ally.com>
Newsgroups: tu-graz.betriebssysteme.linux
Subject: I love Memacs
Date: Thu, 17 Nov 2011 22:02:06 +0100
Message-ID: <2011-11-17T21-58-27@ally.com>
Reply-To: news@ally.com
Content-Type: text/plain; charset=utf-8

i just want to say that i love Memacs
"""
        timestamp, output, notes, properties = \
            MailParser.parse_message(message,
                                     True)

        self.assertEqual(timestamp, "<2011-11-17 Thu 22:02:06>")
        self.assertEqual(output,
                         "[[mailto:alice@ally.com][Alice Ally]]@[[news:tu-" + \
                         "graz.betriebssysteme.linux]" + \
                         "[tu-graz.betriebssysteme.linux]]: I love Memacs")
        self.assertEqual(notes, "i just want to say that i love Memacs\n")
        p = """   :PROPERTIES:\n   :REPLY-TO:   news@ally.com
   :NEWSGROUPS: tu-graz.betriebssysteme.linux
   :ID:         53e60f934645301478db6c9d5d3df71a043f9851
   :END:"""

        self.assertEqual(unicode(properties), p)

########NEW FILE########
__FILENAME__ = orgformat_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-04-08 16:38:19 vk>

import unittest
import time
import os
from memacs.lib.orgformat import OrgFormat


class TestOrgFormat(unittest.TestCase):

    def test_link(self):
        """
        test Org links
        """
        self.assertEqual("[[/link/][description]]",
                         OrgFormat.link("/link/", "description"),
                         "format error link+description")
        self.assertEqual("[[/link/]]",
                         OrgFormat.link("/link/"),
                         "format error link")
        self.assertEqual("[[/link%20link/]]",
                         OrgFormat.link("/link link/"),
                         "quote error")

    def test_date(self):
        """
        test Org date
        """
        # testing tuples
        t = time.strptime("2011-11-02T20:38", "%Y-%m-%dT%H:%M")
        date = OrgFormat.date(t)
        datetime = OrgFormat.date(t, show_time=True)
        self.assertEqual("<2011-11-02 Wed>", date, "date error")
        self.assertEqual("<2011-11-02 Wed 20:38>", datetime, "datetime error")

    def test_inactive_date(self):
        """
        test Org inactive_date
        """
        # testing tuples
        t = time.strptime("2011-11-02T20:38", "%Y-%m-%dT%H:%M")
        date = OrgFormat.inactive_date(t)
        datetime = OrgFormat.inactive_datetime(t)
        self.assertEqual("[2011-11-02 Wed]", date, "date error")
        self.assertEqual("[2011-11-02 Wed 20:38]", datetime, "datetime error")

    def test_strings(self):
        # testing strings
        self.assertEqual("<2011-11-03 Thu>",
                         OrgFormat.strdate("2011-11-3"),
                         "date string error")
        self.assertEqual("<2011-11-03 Thu 11:52>",
                         OrgFormat.strdatetime("2011-11-3 11:52"),
                         "datetime string error")

    def test_iso8601(self):
        # testing iso8601
        self.assertEqual("<2011-11-30 Wed 21:06>",
                         OrgFormat.strdatetimeiso8601("2011-11-30T21.06"),
                         "datetimeiso8601 error")
        self.assertEqual("<2011-11-30 Wed 21:06>",
                         OrgFormat.strdatetimeiso8601("2011-11-30T21.06.00"),
                         "datetimeiso8601 error")
        self.assertEqual("<2011-11-30 Wed 21:06:02>",
                         OrgFormat.strdatetimeiso8601("2011-11-30T21.06.02"),
                         "datetimeiso8601 error")

    def test_iso8601_datetimetupel(self):
        self.assertEqual(
            2011,
            OrgFormat.datetimetupeliso8601("2011-11-30T21.06.02").tm_year,
            "datetimeiso8601 error")
        self.assertEqual(
            11,
            OrgFormat.datetimetupeliso8601("2011-11-30T21.06.02").tm_mon,
            "datetimeiso8601 error")
        self.assertEqual(
            30,
            OrgFormat.datetimetupeliso8601("2011-11-30T21.06.02").tm_mday,
            "datetimeiso8601 error")
        self.assertEqual(
            21,
            OrgFormat.datetimetupeliso8601("2011-11-30T21.06.02").tm_hour,
            "datetimeiso8601 error")
        self.assertEqual(
            6,
            OrgFormat.datetimetupeliso8601("2011-11-30T21.06.02").tm_min,
            "datetimeiso8601 error")
        self.assertEqual(
            2,
            OrgFormat.datetimetupeliso8601("2011-11-30T21.06.02").tm_sec,
            "datetimeiso8601 error")

    def test_iso8601_datetupel(self):
        self.assertEqual(
            2011,
            OrgFormat.datetupeliso8601("2011-11-30").tm_year,
            "datetimeiso8601 error")
        self.assertEqual(
            11,
            OrgFormat.datetupeliso8601("2011-11-30").tm_mon,
            "datetimeiso8601 error")
        self.assertEqual(
            30,
            OrgFormat.datetupeliso8601("2011-11-30").tm_mday,
            "datetimeiso8601 error")

    def test_date_ranges(self):
        daterange = OrgFormat.daterange(
            OrgFormat.datetupeliso8601("2011-11-29"),
            OrgFormat.datetupeliso8601("2011-11-30"))
        self.assertEqual(
            daterange,
            "<2011-11-29 Tue>--<2011-11-30 Wed>")
        datetimerange = OrgFormat.datetimerange(
            OrgFormat.datetimetupeliso8601("2011-11-30T21.06.02"),
            OrgFormat.datetimetupeliso8601("2011-11-30T22.06.02"))
        self.assertEqual(
            datetimerange,
            "<2011-11-30 Wed 21:06:02>--<2011-11-30 Wed 22:06:02>")

    def test_utc_time(self):
        os.environ['TZ'] = "Europe/Vienna"
        time.tzset()
        self.assertEqual(
            OrgFormat.date(
                OrgFormat.datetupelutctimestamp("20111219T205510Z"), True),
            "<2011-12-19 Mon 21:55:10>")
        self.assertEqual(
            OrgFormat.date(OrgFormat.datetupelutctimestamp("20111219T205510"),
                           True),
            "<2011-12-19 Mon 20:55:10>")
        self.assertEqual(
            OrgFormat.date(OrgFormat.datetupelutctimestamp("20111219"), False),
            "<2011-12-19 Mon>")

    def test_contact_mail_mailto_link(self):
        mail_link1 = OrgFormat.contact_mail_mailto_link(
                "Bob Bobby <bob.bobby@example.com>")
        mail_link2 = OrgFormat.contact_mail_mailto_link("<Bob@example.com>")
        self.assertEqual("[[mailto:bob.bobby@example.com][Bob Bobby]]",
                         mail_link1)
        self.assertEqual("[[mailto:Bob@example.com][Bob@example.com]]",
                         mail_link2)

    def test_n(self):
        self.assertEqual("[[news:foo][foo]]", OrgFormat.newsgroup_link("foo"))


    def test_get_hms_from_sec(self):

        self.assertEqual(OrgFormat.get_hms_from_sec(123), '0:02:03')
        self.assertEqual(OrgFormat.get_hms_from_sec(9999), '2:46:39')


    def test_get_dhms_from_sec(self):

        self.assertEqual(OrgFormat.get_dhms_from_sec(123), '0:02:03')
        self.assertEqual(OrgFormat.get_dhms_from_sec(9999), '2:46:39')
        self.assertEqual(OrgFormat.get_dhms_from_sec(99999), '1d 3:46:39')
        self.assertEqual(OrgFormat.get_dhms_from_sec(12345678), '142d 21:21:18')


# Local Variables:
# mode: flyspell
# eval: (ispell-change-dictionary "en_US")
# End:

########NEW FILE########
__FILENAME__ = orgproperty_test
# -*- coding: utf-8 -*-
# Time-stamp: <2011-12-20 15:13:31 awieser>

import unittest
import time
from memacs.lib.orgformat import OrgFormat
from memacs.lib.orgproperty import OrgProperties


class TestOrgProperties(unittest.TestCase):

    def test_properties_default_ctor(self):
        p = OrgProperties("hashing data 1235")
        properties = unicode(p).splitlines()
        self.assertEqual(properties[0], u"   :PROPERTIES:")
        self.assertEqual(properties[1],
            u"   :ID:         063fad7f77461ed6a818b6b79306d641e9c90a83")
        self.assertEqual(properties[2], u"   :END:")

    def test_properties_with_own_created(self):
        p = OrgProperties()
        p.add(u"CREATED",
              OrgFormat.datetime(time.gmtime(0)))
        properties = unicode(p).splitlines()

        self.assertEqual(properties[0], u"   :PROPERTIES:")
        self.assertEqual(properties[1], u"   :CREATED:    <1970-01-0" + \
                         "1 Thu 00:00>")
        self.assertEqual(properties[2], u"   :ID:         fede47e9" + \
                         "f49e1b7f5c6599a6d607e9719ca98625")
        self.assertEqual(properties[3], u"   :END:")

########NEW FILE########
__FILENAME__ = orgwriter_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2012-04-16 22:59:38 armin>

import unittest
import os
import codecs
import time
from memacs.lib.orgformat import OrgFormat
from memacs.lib.orgwriter import OrgOutputWriter
from memacs.lib.orgproperty import OrgProperties


class TestOutputWriter(unittest.TestCase):
    def setUp(self):
        # setting tmpfolder to "./tmp"
        self.TMPFOLDER = os.path.normpath(
            os.path.dirname(os.path.abspath(__file__)) + \
                os.path.sep + "tmp") + os.sep
        if not os.path.exists(self.TMPFOLDER):
            os.makedirs(self.TMPFOLDER)

    def test_ouput_to_file(self):
        """
        Simple Test
        """
        test_filename = self.TMPFOLDER + "testfile.org"

        properties = OrgProperties("data_for_hashing")

        # writing test output
        writer = OrgOutputWriter("short descript", "test-tag", test_filename)
        writer.write("## abc\n")
        writer.writeln("## abc")
        writer.write_comment("abc\n")
        writer.write_commentln("abc")
        writer.write_org_item("begin")

        timestamp = OrgFormat.datetime(time.gmtime(0))
        writer.write_org_subitem(timestamp=timestamp,
                                 output="sub",
                                 properties=properties)
        writer.write_org_subitem(timestamp=timestamp,
                                 output="sub",
                                 tags=["foo", "bar"],
                                 properties=properties)
        writer.close()

        # read and check the file_handler
        file_handler = codecs.open(test_filename, "r", "utf-8")
        data = file_handler.readlines()

        #for d in range(len(data)):
        #   print "self.assertEqual(\n\tdata[%d],\n\t\"%s\")" % \
        #       (d, data[d])

#        self.assertEqual(
#            data[1],
#            "## this file is generated by "...
#        ")
#        self.assertEqual(
#            data[2],
#            "## To add this file to your org-agenda " ...
#        ")
        self.assertEqual(
            data[3],
            "* short descript          :Memacs:test-tag:\n")
        self.assertEqual(
            data[4],
            "## abc\n")
        self.assertEqual(
            data[5],
            "## abc\n")
        self.assertEqual(
            data[6],
            "## abc\n")
        self.assertEqual(
            data[7],
            "## abc\n")
        self.assertEqual(
            data[8],
            "* begin\n")
        self.assertEqual(
            data[9],
            "** <1970-01-01 Thu 00:00> sub\n")
        self.assertEqual(
            data[10],
            "   :PROPERTIES:\n")
        self.assertEqual(
            data[11],
            "   :ID:         9cc53a63e13e18437401513316185f6f3b7ed703\n")
        self.assertEqual(
            data[12],
            "   :END:\n")
        self.assertEqual(
            data[13],
            "\n")
        self.assertEqual(
            data[14],
            "** <1970-01-01 Thu 00:00> sub\t:foo:bar:\n")
        self.assertEqual(
            data[15],
            "   :PROPERTIES:\n")
        self.assertEqual(
            data[16],
            "   :ID:         9cc53a63e13e18437401513316185f6f3b7ed703\n")
        self.assertEqual(
            data[17],
            "   :END:\n")
        #cleaning up
        file_handler.close()
        os.remove(self.TMPFOLDER + "testfile.org")

    def test_utf8(self):
        test_filename = self.TMPFOLDER + "testutf8.org"

        # writing test output
        writer = OrgOutputWriter("short-des", "tag", test_filename)
        writer.write(u"☁☂☃☄★☆☇☈☉☊☋☌☍☎☏☐☑☒☓☔☕☖☗♞♟♠♡♢♣♤♥♦♧♨♩♪♫♬♭♮♯♰♱♲♳♴♵\n")
        writer.close()

        # read and check the file_handler
        file_handler = codecs.open(test_filename, "r", "utf-8")
        input_handler = file_handler.readlines()
        file_handler.close()
        self.assertEqual(input_handler[4],
                         u"☁☂☃☄★☆☇☈☉☊☋☌☍☎☏☐☑☒☓☔☕☖☗♞♟♠♡♢♣♤♥♦♧♨♩♪♫♬♭♮♯♰♱♲♳♴♵\n",
                         "utf-8 failure")

        #cleaning up

        os.remove(self.TMPFOLDER + "testutf8.org")

    def test_autotag(self):
        test_filename = self.TMPFOLDER + "testautotag.org"

        autotag_dict = {}
        autotag_dict["TUG"] = ["tugraz", "university"]
        autotag_dict["programming"] = ["programming", "python", "java"]

        output = "Programming for my bachelor thesis at University"

        # writing test output
        writer = OrgOutputWriter(short_description="short-des",
                                 tag="tag",
                                 file_name=test_filename,
                                 autotag_dict=autotag_dict)
        timestamp = OrgFormat.datetime(time.gmtime(0))

        properties = OrgProperties("data_for_hashing")

        writer.write_org_subitem(timestamp=timestamp,
                                 output=output,
                                 properties=properties)
        writer.close()

        # read and check the file_handler
        file_handler = codecs.open(test_filename, "r", "utf-8")
        input_handler = file_handler.readlines()
        file_handler.close()

        self.assertEqual(input_handler[4],
                         u"** <1970-01-01 Thu 00:00> Programming for my " + \
                         "bachelor thesis at University\t:programming:TUG:\n")

        #cleaning up
        os.remove(self.TMPFOLDER + "testautotag.org")

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = reader_test
# -*- coding: utf-8 -*-
# Time-stamp: <2011-12-30 12:16:47 armin>

import unittest
from memacs.lib.reader import CommonReader


class TestReader(unittest.TestCase):

    def test_file_no_path(self):
        try:
            CommonReader.get_data_from_file("")
            self.assertTrue(False, "false path failed")
        except SystemExit:
            pass

########NEW FILE########
__FILENAME__ = phonecalls
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-05-02 20:36:03 vk>

import sys
import os
import logging
import xml.sax
import time, datetime
from xml.sax._exceptions import SAXParseException
from lib.orgformat import OrgFormat
from lib.memacs import Memacs
from lib.reader import CommonReader
from lib.orgproperty import OrgProperties
#import pdb

class PhonecallsSaxHandler(xml.sax.handler.ContentHandler):
    """
    Sax handler for following xml's:
    2013-04-10: update: contact_name is also recognized

    <?xml version='1.0' encoding='UTF-8' standalone='yes' ?>

    <calls count="8">
      <call number="+43691234123" duration="59" date="13193906092" type="1" />
      <call number="06612341234" duration="22" date="131254215834" type="2" />
      <call number="-1" duration="382" date="1312530691081" type="1" />
      <call number="+4312341234" duration="289" date="13124327195" type="1" />
      <call number="+4366412341234" duration="70" date="136334059" type="1" />
      <call number="+4366234123" duration="0" date="1312473751975" type="2" />
      <call number="+436612341234" duration="0" date="12471300072" type="3" />
      <call number="+433123412" duration="60" date="1312468562489" type="2" />
    </calls>"""

    def __init__(self,
                 writer,
                 ignore_incoming,
                 ignore_outgoing,
                 ignore_missed,
                 minimum_duration
                 ):
        """
        Ctor

        @param writer: orgwriter
        @param ignore_incoming: ignore incoming phonecalls
        @param ignore_outgoing: ignore outgoing phonecalls
        @param ignore_missed:   ignore missed   phonecalls
        @param minimum_duration:    ignore phonecalls less than that time
        """
        self._writer = writer
        self._ignore_incoming = ignore_incoming
        self._ignore_outgoing = ignore_outgoing
        self._ignore_missed = ignore_missed
        self._minimum_duration = minimum_duration

    def startElement(self, name, attrs):
        """
        at every <call> write to orgfile
        """
        logging.debug("Handler @startElement name=%s,attrs=%s", name, attrs)

        if name == "call":
            call_number = attrs['number']
            call_duration = int(attrs['duration'])
            call_date = int(attrs['date']) / 1000     # unix epoch

            call_type = int(attrs['type'])
            call_incoming = call_type == 1
            call_outgoing = call_type == 2
            call_missed = call_type == 3

            call_name = call_number
            if 'contact_name' in attrs:
                ## NOTE: older version of backup app did not insert contact_name into XML
                call_name = attrs['contact_name']

            output = "Phonecall "

            skip = False

            if call_incoming:
                output += "from "
                if self._ignore_incoming:
                    skip = True
            elif call_outgoing:
                output += "to "
                if self._ignore_outgoing:
                    skip = True
            elif call_missed:
                output += "missed "
                if self._ignore_missed:
                    skip = True
            else:
                raise Exception("Invalid Phonecall Type: %d", call_type)

            call_number_string = ""
            if call_number != "-1":
                call_number_string = call_number
            else:
                call_number_string = "Unknown Number"

            name_string = ""
            if call_name != "(Unknown)":
                name_string = '[[contact:' + call_name + '][' + call_name + ']]'
            else:
                name_string = "Unknown"
            output += name_string

            if call_duration < self._minimum_duration:
                skip = True

            timestamp = OrgFormat.datetime(time.gmtime(call_date))

            end_datetimestamp = datetime.datetime.utcfromtimestamp(call_date + call_duration)
            logging.debug("timestamp[%s] duration[%s] end[%s]" % 
                          (str(timestamp), str(call_duration), str(end_datetimestamp)))

            end_timestamp_string = OrgFormat.datetime(end_datetimestamp)
            logging.debug("end_time [%s]" % end_timestamp_string)

            data_for_hashing = output + timestamp
            properties = OrgProperties(data_for_hashing=data_for_hashing)
            properties.add("NUMBER", call_number_string)
            properties.add("DURATION", call_duration)
            properties.add("NAME", call_name)

            if not skip:
                self._writer.write_org_subitem(output=output,
                                               timestamp=timestamp + '-' + end_timestamp_string,
                                               properties=properties
                                               )


class PhonecallsMemacs(Memacs):
    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        self._parser.add_argument(
            "-f", "--file", dest="smsxmlfile",
            action="store", required=True,
            help="path to sms xml backup file")

        self._parser.add_argument(
            "--ignore-incoming", dest="ignore_incoming",
            action="store_true",
            help="ignore incoming phonecalls")

        self._parser.add_argument(
            "--ignore-outgoing", dest="ignore_outgoing",
            action="store_true",
            help="ignore outgoing phonecalls")

        self._parser.add_argument(
            "--ignore-missed", dest="ignore_missed",
            action="store_true",
            help="ignore outgoing phonecalls")

        self._parser.add_argument(
            "--minimum-duration", dest="minimum_duration",
            action="store", type=int,
            help="[sec] show only calls with duration >= this argument")


    def _parser_parse_args(self):
        """
        overwritten method of class Memacs

        all additional arguments are parsed in here
        """
        Memacs._parser_parse_args(self)
        if not (os.path.exists(self._args.smsxmlfile) or \
                     os.access(self._args.smsxmlfile, os.R_OK)):
            self._parser.error("input file not found or not readable")


    def _main(self):
        """
        gets called automatically from Memacs class.
        read the lines from phonecalls backup xml file,
        parse and write them to org file
        """

        data = CommonReader.get_data_from_file(self._args.smsxmlfile)

        try:
            xml.sax.parseString(data.encode('utf-8'),
                                PhonecallsSaxHandler(self._writer,
                                              self._args.ignore_incoming,
                                              self._args.ignore_outgoing,
                                              self._args.ignore_missed,
                                              self._args.minimum_duration,
                                              ))
        except SAXParseException:
            logging.error("No correct XML given")
            sys.exit(1)

########NEW FILE########
__FILENAME__ = phonecalls_superbackup
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-05-02 20:36:03 vk>

import sys
import os
import logging
import xml.sax
import time, datetime
from xml.sax._exceptions import SAXParseException
from lib.orgformat import OrgFormat
from lib.memacs import Memacs
from lib.reader import CommonReader
from lib.orgproperty import OrgProperties
#import pdb

logging.basicConfig(filename='debug.log', level=logging.DEBUG)

class PhonecallsSaxHandler(xml.sax.handler.ContentHandler):
    """
    Sax handler for following xml's:

    <?xml version="1.0" encoding="UTF-8"?>
    <alllogs count="500">
            <log number="01270811333" time="3 Sep 2013 10:03:26" date="1378199006383" type="1" name="" new="1" dur="30" />
            <log number="01270588896" time="1 Sep 2013 19:41:05" date="1378060865117" type="2" name="Nick Powell" new="1" dur="143" />
            <log number="07989385391" time="1 Sep 2013 13:41:23" date="1378039283149" type="1" name="Anne Barton" new="1" dur="19" />
            <log number="+447943549963" time="1 Sep 2013 13:26:31" date="1378038391562" type="2" name="John M Barton" new="1" dur="0" />
            <log number="+447943549963" time="1 Sep 2013 13:11:46" date="1378037506896" type="2" name="John M Barton" new="1" dur="0" />

    </alllogs>


    def __init__(self,
                 writer,
                 ignore_incoming,
                 ignore_outgoing,
                 ignore_missed,
                 minimum_duration
                 ):
        """
        Ctor

        @param writer: orgwriter
        @param ignore_incoming: ignore incoming phonecalls
        @param ignore_outgoing: ignore outgoing phonecalls
        @param ignore_missed:   ignore missed   phonecalls
        @param minimum_duration:    ignore phonecalls less than that time
        """
        self._writer = writer
        self._ignore_incoming = ignore_incoming
        self._ignore_outgoing = ignore_outgoing
        self._ignore_missed = ignore_missed
        self._minimum_duration = minimum_duration

    def startElement(self, name, attrs):
        """
        at every <log> write to orgfile
        """
        logging.debug("Handler @startElement name=%s,attrs=%s", name, attrs)

        if name == "log":
            call_number = attrs['number']
            call_duration = int(attrs['dur'])

            call_date = int(attrs['date']) / 1000     # unix epoch

            call_type = int(attrs['type'])
            call_incoming = call_type == 1
            call_outgoing = call_type == 2
            call_missed = call_type == 3

            call_name = attrs['name']

            output = "Phonecall "

            skip = False

            if call_incoming:
                output += "from "
                if self._ignore_incoming:
                    skip = True
            elif call_outgoing:
                output += "to "
                if self._ignore_outgoing:
                    skip = True
            elif call_missed:
                output += "missed "
                if self._ignore_missed:
                    skip = True
            else:
                raise Exception("Invalid Phonecall Type: %d", call_type)

            call_number_string = ""
            if call_number != "-1":
                call_number_string = call_number
            else:
                call_number_string = "Unknown Number"

            name_string = ""
            if call_name != "(Unknown)":
                name_string = '[[contact:' + call_name + '][' + call_name + ']]'
            else:
                name_string = "Unknown"
            output += name_string

            if call_duration < self._minimum_duration:
                skip = True

            timestamp = OrgFormat.datetime(time.gmtime(call_date))

            end_datetimestamp = datetime.datetime.utcfromtimestamp(call_date + call_duration)
            logging.debug("timestamp[%s] duration[%s] end[%s]" %
                          (str(timestamp), str(call_duration), str(end_datetimestamp)))

            end_timestamp_string = OrgFormat.datetime(end_datetimestamp)
            logging.debug("end_time [%s]" % end_timestamp_string)

            data_for_hashing = output + timestamp
            properties = OrgProperties(data_for_hashing=data_for_hashing)
            properties.add("NUMBER", call_number_string)
            properties.add("DURATION", call_duration)
            properties.add("NAME", call_name)

            if not skip:
                self._writer.write_org_subitem(output=output,
                                               timestamp=timestamp + '-' + end_timestamp_string,
                                               properties=properties
                                               )


class PhonecallsSuperBackupMemacs(Memacs):
    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        self._parser.add_argument(
            "-f", "--file", dest="smsxmlfile",
            action="store", required=True,
            help="path to sms xml backup file")

        self._parser.add_argument(
            "--ignore-incoming", dest="ignore_incoming",
            action="store_true",
            help="ignore incoming phonecalls")

        self._parser.add_argument(
            "--ignore-outgoing", dest="ignore_outgoing",
            action="store_true",
            help="ignore outgoing phonecalls")

        self._parser.add_argument(
            "--ignore-missed", dest="ignore_missed",
            action="store_true",
            help="ignore outgoing phonecalls")

        self._parser.add_argument(
            "--minimum-duration", dest="minimum_duration",
            action="store", type=int,
            help="[sec] show only calls with duration >= this argument")


    def _parser_parse_args(self):
        """
        overwritten method of class Memacs

        all additional arguments are parsed in here
        """
        Memacs._parser_parse_args(self)
        if not (os.path.exists(self._args.smsxmlfile) or \
                     os.access(self._args.smsxmlfile, os.R_OK)):
            self._parser.error("input file not found or not readable")


    def _main(self):
        """
        gets called automatically from Memacs class.
        read the lines from phonecalls backup xml file,
        parse and write them to org file
        """

        data = CommonReader.get_data_from_file(self._args.smsxmlfile)

        try:
            xml.sax.parseString(data.encode('utf-8'),
                                PhonecallsSaxHandler(self._writer,
                                              self._args.ignore_incoming,
                                              self._args.ignore_outgoing,
                                              self._args.ignore_missed,
                                              self._args.minimum_duration,
                                              ))
        except SAXParseException:
            logging.error("No correct XML given")
            sys.exit(1)

########NEW FILE########
__FILENAME__ = photos
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2014-05-03 17:49:30 vk>

import os
import logging
import time
from lib.orgformat import OrgFormat
from lib.memacs import Memacs
from lib.orgproperty import OrgProperties
import imghdr
from PIL import Image
from PIL.ExifTags import TAGS


def get_exif_datetime(filename):
    """
    Get datetime of exif information of a file
    """

    try:
        exif_data_decoded = {}
        image = Image.open(filename)
        if hasattr(image, '_getexif'):
            exif_info = image._getexif()
            if exif_info != None:
                for tag, value in exif_info.items():
                    decoded_tag = TAGS.get(tag, tag)
                    exif_data_decoded[decoded_tag] = value

        if "DateTime" in exif_data_decoded.keys():
            return exif_data_decoded["DateTime"]
        if "DateTimeOriginal" in exif_data_decoded.keys():
            return exif_data_decoded["DateTimeOriginal"]

    except IOError, e:
        logging.warning("IOError at %s:", filename, e)

    return None


class PhotosMemacs(Memacs):
    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        self._parser.add_argument(
            "-f", "--folder", dest="photo_folder",
            action="store", required=True,
            help="path to search for photos")

        self._parser.add_argument("-l", "--follow-links",
                                  dest="follow_links", action="store_true",
                                  help="follow symbolics links," + \
                                      " default False")

    def _parser_parse_args(self):
        """
        overwritten method of class Memacs

        all additional arguments are parsed in here
        """
        Memacs._parser_parse_args(self)
        if not os.path.exists(self._args.photo_folder):
            self._parser.error("photo folder does not exist")

    def __handle_file(self, photo_file, filename):
        """
        checks if file is an image, try to get exif data and
        write to org file
        """

        logging.debug("handling file %s", filename)

        # check if file is an image:
        if imghdr.what(filename) != None:
            datetime = get_exif_datetime(filename)
            if datetime == None:
                logging.debug("skipping: %s has no EXIF information", filename)
            else:
                try:
                    datetime = time.strptime(datetime, "%Y:%m:%d %H:%M:%S")
                    timestamp = OrgFormat.datetime(datetime)
                    output = OrgFormat.link(filename, photo_file)
                    properties = OrgProperties(photo_file + timestamp)

                    self._writer.write_org_subitem(timestamp=timestamp,
                                                   output=output,
                                                   properties=properties)
                except ValueError, e:
                    logging.warning("skipping: Could not parse " + \
                                    "timestamp for %s : %s", filename, e)

    def _main(self):
        """
        get's automatically called from Memacs class
        walk through given folder and handle each file
        """

        for rootdir, dirs, files in os.walk(self._args.photo_folder,
                                    followlinks=self._args.follow_links):
            for photo_file in files:
                filename = rootdir + os.sep + photo_file
                self.__handle_file(photo_file, filename)

########NEW FILE########
__FILENAME__ = rss
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2011-10-28 15:13:31 aw>

import sys
import os
import logging
import feedparser
import calendar
import time
import re
from lib.reader import CommonReader
from lib.orgproperty import OrgProperties
from lib.orgformat import OrgFormat
from lib.memacs import Memacs


class RssMemacs(Memacs):
    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        self._parser.add_argument(
           "-u", "--url", dest="url",
           action="store",
           help="url to a rss file")

        self._parser.add_argument(
           "-f", "--file", dest="file",
           action="store",
           help="path to rss file")

    def _parser_parse_args(self):
        """
        overwritten method of class Memacs

        all additional arguments are parsed in here
        """
        Memacs._parser_parse_args(self)
        if self._args.url and self._args.file:
            self._parser.error("you cannot set both url and file")

        if not self._args.url and not self._args.file:
            self._parser.error("please specify a file or url")

        if self._args.file:
            if not os.path.exists(self._args.file):
                self._parser.error("file %s not readable", self._args.file)
            if not os.access(self._args.file, os.R_OK):
                self._parser.error("file %s not readable", self._args.file)

    def __get_item_data(self, item):
        """
        gets information out of <item>..</item>

        @return:  output, note, properties, tags
                  variables for orgwriter.append_org_subitem
        """
        try:
            #logging.debug(item)
            properties = OrgProperties()
            guid = item['id']
            if not guid:
                logging.error("got no id")

            unformatted_link = item['link']
            short_link = OrgFormat.link(unformatted_link, "link")

            # if we found a url in title
            # then append the url in front of subject
            if re.search("http[s]?://", item['title']) != None:
                output = short_link + ": " + item['title']
            else:
                output = OrgFormat.link(unformatted_link, item['title'])

            note = item['description']

            # converting updated_parsed UTC --> LOCALTIME
            timestamp = OrgFormat.datetime(
                time.localtime(calendar.timegm(item['updated_parsed'])))

            properties.add("guid", guid)

        except KeyError:
            logging.error("input is not a RSS 2.0")
            sys.exit(1)

        tags = []
        dont_parse = ['title', 'description', 'updated', 'summary',
                          'updated_parsed', 'link', 'links']
        for i in  item:
            logging.debug(i)
            if i not in dont_parse:
                if (type(i) == unicode or type(i) == str) and \
                type(item[i]) == unicode and  item[i] != "":
                    if i == "id":
                        i = "guid"
                    properties.add(i, item[i])
                else:
                    if i == "tags":
                        for tag in item[i]:
                            logging.debug("found tag: %s", tag['term'])
                            tags.append(tag['term'])

        return output, note, properties, tags, timestamp

    def _main(self):
        """
        get's automatically called from Memacs class
        """
        # getting data
        if self._args.file:
            data = CommonReader.get_data_from_file(self._args.file)
        elif self._args.url:
            data = CommonReader.get_data_from_url(self._args.url)

        rss = feedparser.parse(data)
        logging.info("title: %s", rss['feed']['title'])
        logging.info("there are: %d entries", len(rss.entries))

        for item in rss.entries:
            logging.debug(item)
            output, note, properties, tags, timestamp = \
                self.__get_item_data(item)
            self._writer.write_org_subitem(output=output,
                                           timestamp=timestamp,
                                           note=note,
                                           properties=properties,
                                           tags=tags)

########NEW FILE########
__FILENAME__ = simplephonelogs
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2014-03-05 20:08:08 vk>

import sys
import os
import re
import logging
import time
import datetime
from lib.orgformat import OrgFormat
from lib.memacs import Memacs
from lib.reader import CommonReader
from lib.orgproperty import OrgProperties
#import pdb  ## pdb.set_trace()  ## FIXXME





class SimplePhoneLogsMemacs(Memacs):

    _REGEX_SEPARATOR = " *?# *?"

    ## match for example: "2012-11-20 # 19.59 # shutdown #   72 # 35682"
    ##                     0            1  2    3            4    5
    LOGFILEENTRY_REGEX = re.compile("([12]\d\d\d-[012345]\d-[012345]\d)" +
                                    _REGEX_SEPARATOR +
                                    "([ 012]\d)[:.]([012345]\d)" +
                                    _REGEX_SEPARATOR +
                                    "(.+)" +
                                    _REGEX_SEPARATOR +
                                    "(\d+)" +
                                    _REGEX_SEPARATOR +
                                    "(\d+)$", flags = re.U)
    RE_ID_DATESTAMP = 0
    RE_ID_HOURS = 1
    RE_ID_MINUTES = 2
    RE_ID_NAME = 3
    RE_ID_BATT = 4
    RE_ID_UPTIME = 5


    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        self._parser.add_argument(
            "-f", "--file", dest="phonelogfile",
            action="store", required=True,
            help="path to phone log file")


    def _parser_parse_args(self):
        """
        overwritten method of class Memacs

        all additional arguments are parsed in here
        """
        Memacs._parser_parse_args(self)
        if not (os.path.exists(self._args.phonelogfile) or \
                     os.access(self._args.phonelogfile, os.R_OK)):
            self._parser.error("input file not found or not readable")




    def _generateOrgentry(self, e_time, e_name, e_batt, e_uptime, 
                          e_last_opposite_occurrence, e_last_occurrence, 
                          prev_office_sum, prev_office_first_begin):
        """
        takes the data from the parameters and generates an Org-mode entry.

        @param e_time: time-stamp of the entry
        @param e_name: entry name/description
        @param e_batt: battery level
        @param e_uptime: uptime in seconds
        @param e_last_opposite_occurrence: time-stamp of previous opposite occurrence (if not False)
        @param e_last_occurrence: time-stamp of previous occurrence
        @param additional_paren_string: string that gets appended to the parenthesis 
        @param prev_office_sum: holds the sum of all previous working duration today
        @param prev_office_first_begin: holds the first time-stamp of wifi-office for today
        """

        assert e_time.__class__ == datetime.datetime
        assert e_name.__class__ == unicode
        assert e_batt.__class__ == unicode
        assert e_uptime.__class__ == unicode
        assert (e_last_opposite_occurrence.__class__ == datetime.datetime or not e_last_opposite_occurrence)
        assert (e_last_occurrence.__class__ == datetime.datetime or not e_last_occurrence)

        last_info = u''
        in_between_hms = u''
        in_between_s = u''
        ignore_occurrence = False

        ## convert parameters to be writable:
        office_sum = prev_office_sum
        office_first_begin = prev_office_first_begin

        if e_last_opposite_occurrence:

            in_between_s = (e_time - e_last_opposite_occurrence).seconds + \
                (e_time - e_last_opposite_occurrence).days * 3600 * 24
            in_between_hms = unicode(OrgFormat.get_hms_from_sec(in_between_s))

            if e_name == u'boot':
                last_info = u' (off for '
            elif e_name == u'shutdown':
                last_info = u' (on for '
            elif e_name.endswith(u'-end'):
                last_info = u' (' + e_name[0:-4].replace('wifi-','') + u' for '
            else:
                last_info = u' (not ' + e_name.replace('wifi-','') + u' for '

            ## handle special case: office hours
            additional_paren_string = ""
            if e_name == 'wifi-office-end':
                office_total = None
                ## calculate office_sum and office_total
                if not office_sum:
                    office_sum = (e_time - e_last_opposite_occurrence).seconds
                    office_total = office_sum
                else:
                    assert(office_first_begin)
                    assert(office_sum)
                    office_sum = office_sum + (e_time - e_last_opposite_occurrence).seconds
                    office_total = int(time.mktime(e_time.timetuple()) - time.mktime(office_first_begin.timetuple()))

                assert(type(office_total) == int)
                assert(type(office_sum) == int)
                assert(type(in_between_s) == int)

                ## come up with the additional office-hours string:
                additional_paren_string = u'; today ' + OrgFormat.get_hms_from_sec(office_sum) + \
                    '; today total ' + OrgFormat.get_hms_from_sec(office_total)

            if additional_paren_string:
                last_info += unicode(OrgFormat.get_dhms_from_sec(in_between_s)) + additional_paren_string + u')'
            else:
                last_info += unicode(OrgFormat.get_dhms_from_sec(in_between_s)) + u')'

        ## handle special case: office hours
        if e_name == 'wifi-office':
            if not office_sum or not office_first_begin:
                ## new day
                office_first_begin = e_time

        ## handle special case: boot without previous shutdown = crash
        if (e_name == u'boot') and \
                (e_last_occurrence and e_last_opposite_occurrence) and \
                (e_last_occurrence > e_last_opposite_occurrence):
            ## last boot is more recent than last shutdown -> crash has happened
            last_info = u' after crash'
            in_between_hms = u''
            in_between_s = u''
            ignore_occurrence = True

        properties = OrgProperties()
        properties.add("IN-BETWEEN", in_between_hms)
        properties.add("IN-BETWEEN-S", unicode(in_between_s))
        properties.add("BATT-LEVEL", e_batt)
        properties.add("UPTIME", OrgFormat.get_hms_from_sec(int(e_uptime)))
        properties.add("UPTIME-S", e_uptime)
        self._writer.write_org_subitem(timestamp = e_time.strftime('<%Y-%m-%d %a %H:%M>'),
                                       output = e_name + last_info,
                                       properties = properties)

            ## the programmer recommends you to read "memacs/tests/simplephonelogs_test.py"
            ## test_generateOrgentry_* for less cryptic examples on how this looks:
        return u'** ' + e_time.strftime('<%Y-%m-%d %a %H:%M>') + u' ' + e_name + last_info + \
            u'\n:PROPERTIES:\n:IN-BETWEEN: ' + in_between_hms + \
            u'\n:IN-BETWEEN-S: ' + unicode(in_between_s) + \
            u'\n:BATT-LEVEL: ' + e_batt + \
            u'\n:UPTIME: ' + unicode(OrgFormat.get_hms_from_sec(int(e_uptime))) + \
            u'\n:UPTIME-S: ' + unicode(e_uptime) + u'\n:END:\n', \
            ignore_occurrence, office_sum, office_first_begin


    def _determine_opposite_eventname(self, e_name):
        """
        Takes a look at the event and returns the name of the opposite event description.
        Opposite of 'boot' is 'shutdown' (and vice versa). 
        Opposite of 'foo' is 'foo-end' (and vice versa).

        @param e_name: string of an event name/description
        """

        assert (e_name.__class__ == unicode)

        if e_name == u'boot':
            return u'shutdown'
        elif e_name == u'shutdown':
            return u'boot'
        elif e_name.endswith(u'-end'):
            return e_name[0:-4]
        else:
            return e_name + u'-end'


    def _parse_data(self, data):
        """parses the phone log data"""

        last_occurrences = { }  ## holds the last occurrences of each event

        office_day = None  ## holds the current day (in order to recognize day change)
        office_first_begin = None  ## holds the time-stamp of the first appearance of wifi-office
        office_sum = None  ## holds the sum of periods of all office-durations for this day

        for line in data.split('\n'):

            if not line:
                continue

            logging.debug("line: %s", line)

            components = re.match(self.LOGFILEENTRY_REGEX, line)
            additional_paren_string = None  ## optional string for the parenthesis (in output header)

            if components:
                logging.debug("line matches")
            else:
                logging.debug("line does not match! (skipping this line)")
                continue

            ## extracting the components to easy to use variables:
            datestamp = components.groups()[self.RE_ID_DATESTAMP].strip()
            hours = int(components.groups()[self.RE_ID_HOURS].strip())
            minutes = int(components.groups()[self.RE_ID_MINUTES].strip())
            e_name = unicode(components.groups()[self.RE_ID_NAME].strip())
            e_batt = components.groups()[self.RE_ID_BATT].strip()
            e_uptime = components.groups()[self.RE_ID_UPTIME].strip()

            ## generating a datestamp object from the time information:
            e_time = datetime.datetime(int(datestamp.split('-')[0]),
                                       int(datestamp.split('-')[1]),
                                       int(datestamp.split('-')[2]),
                                       hours, minutes)

            ## resetting office_day
            if e_name == 'wifi-office':
                if not office_day:
                    office_sum = None
                    office_day = datestamp
                elif office_day != datestamp:
                    office_sum = None
                    office_day = datestamp

            # if e_name == 'wifi-office-end':
            #     if not office_day:
            #         logging.error('On ' + datestamp + ' I found \"wifi-office-end\" without a begin. ' + \
            #                           'Please do not work after midnight ;-)')

            opposite_e_name = self._determine_opposite_eventname(e_name)
            if opposite_e_name in last_occurrences:
                e_last_opposite_occurrence = last_occurrences[opposite_e_name]
            else:
                ## no previous occurrence of the opposite event type
                e_last_opposite_occurrence = False

            if e_name in last_occurrences:
                last_time = last_occurrences[e_name]
            else:
                last_time = False

            result, ignore_occurrence, office_sum, office_first_begin = \
                self._generateOrgentry(e_time, e_name, e_batt, 
                                       e_uptime, 
                                       e_last_opposite_occurrence,
                                       last_time,
                                       office_sum, office_first_begin)

            ## update last_occurrences-dict
            if not ignore_occurrence:
                last_occurrences[e_name] = e_time

            
    def _main(self):
        """
        gets called automatically from Memacs class.
        read the lines from phonecalls backup xml file,
        parse and write them to org file
        """

        self._parse_data(CommonReader.get_data_from_file(self._args.phonelogfile))



# Local Variables:
# mode: flyspell
# eval: (ispell-change-dictionary "en_US")
# End:

########NEW FILE########
__FILENAME__ = sms
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-05-02 20:39:34 vk>

import sys
import os
import logging
import xml.sax
import time
from xml.sax._exceptions import SAXParseException
from lib.orgformat import OrgFormat
from lib.orgproperty import OrgProperties
from lib.memacs import Memacs
from lib.reader import CommonReader


class SmsSaxHandler(xml.sax.handler.ContentHandler):
    """
    Sax handler for sms backup xml files.
    See documentation memacs_sms.org for an example.
    """

    def __init__(self, writer, ignore_incoming, ignore_outgoing):
        """
        Ctor

        @param writer: orgwriter
        @param ignore_incoming: ignore incoming smses
        """
        self._writer = writer
        self._ignore_incoming = ignore_incoming
        self._ignore_outgoing = ignore_outgoing

    def startElement(self, name, attrs):
        """
        at every <sms> tag write to orgfile
        """
        logging.debug("Handler @startElement name=%s,attrs=%s", name, attrs)

        if name == "sms":
            sms_subject = attrs['subject']
            sms_date = int(attrs['date']) / 1000     # unix epoch
            sms_body = attrs['body']
            sms_address = attrs['address']
            sms_type_incoming = int(attrs['type']) == 1
            contact_name = False
            if 'contact_name' in attrs:
                ## NOTE: older version of backup app did not insert contact_name into XML
                contact_name = attrs['contact_name']

            skip = False

            if sms_type_incoming == True:
                output = "SMS from "
                if self._ignore_incoming:
                    skip = True
            else:
                output = "SMS to "
                if self._ignore_outgoing:
                    skip = True

            if not skip:
    
                name_string = ""
                if contact_name:
                    name_string = '[[contact:' + contact_name + '][' + contact_name + ']]'
                else:
                    name_string = "Unknown"
                output += name_string + ": "
    
                if sms_subject != "null":
                    # in case of MMS we have a subject
                    output += sms_subject
                    notes = sms_body
                else:
                    output += sms_body
                    notes = ""

                timestamp = OrgFormat.datetime(time.gmtime(sms_date))
                data_for_hashing = output + timestamp + notes
                properties = OrgProperties(data_for_hashing=data_for_hashing)

                properties.add("NUMBER", sms_address)
                properties.add("NAME", contact_name)

                self._writer.write_org_subitem(output=output,
                                               timestamp=timestamp,
                                               note=notes,
                                               properties=properties)


class SmsMemacs(Memacs):
    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        self._parser.add_argument(
            "-f", "--file", dest="smsxmlfile",
            action="store", required=True,
            help="path to sms xml backup file")

        self._parser.add_argument(
            "--ignore-incoming", dest="ignore_incoming",
            action="store_true",
            help="ignore incoming smses")

        self._parser.add_argument(
            "--ignore-outgoing", dest="ignore_outgoing",
            action="store_true",
            help="ignore outgoing smses")

    def _parser_parse_args(self):
        """
        overwritten method of class Memacs

        all additional arguments are parsed in here
        """
        Memacs._parser_parse_args(self)
        if not (os.path.exists(self._args.smsxmlfile) or \
                     os.access(self._args.smsxmlfile, os.R_OK)):
            self._parser.error("input file not found or not readable")

    def _main(self):
        """
        get's automatically called from Memacs class
        read the lines from sms backup xml file,
        parse and write them to org file
        """

        data = CommonReader.get_data_from_file(self._args.smsxmlfile)

        try:
            xml.sax.parseString(data.encode('utf-8'),
                                SmsSaxHandler(self._writer,
                                              self._args.ignore_incoming,
                                              self._args.ignore_outgoing))
        except SAXParseException:
            logging.error("No correct XML given")
            sys.exit(1)

########NEW FILE########
__FILENAME__ = sms_superbackup
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-05-02 20:39:34 vk>

import sys
import os
import logging
import xml.sax
import time
from xml.sax._exceptions import SAXParseException
from lib.orgformat import OrgFormat
from lib.orgproperty import OrgProperties
from lib.memacs import Memacs
from lib.reader import CommonReader


class SmsSaxHandler(xml.sax.handler.ContentHandler):
    """
    Sax handler for sms backup xml produced by SuperBackup files.
    See documentation memacs_sms.org for an example.
    """

    def __init__(self, writer, ignore_incoming, ignore_outgoing):
        """
        Ctor

        @param writer: orgwriter
        @param ignore_incoming: ignore incoming smses
        """
        self._writer = writer
        self._ignore_incoming = ignore_incoming
        self._ignore_outgoing = ignore_outgoing

    def startElement(self, name, attrs):
        """
        at every <sms> tag write to orgfile
        """
        logging.debug("Handler @startElement name=%s,attrs=%s", name, attrs)

        if name == "sms":
            #sms_subject = attrs['subject']
            sms_date = int(attrs['date']) / 1000     # unix epoch
            sms_body = attrs['body']
            sms_address = attrs['address']
            sms_time = attrs['time']
            sms_service_center = attrs['service_center']
            sms_type_incoming = int(attrs['type']) == 1
            contact_name = attrs['name']

            skip = False

            if sms_type_incoming == True:
                output = "SMS from "
                if self._ignore_incoming:
                    skip = True
            else:
                output = "SMS to "
                if self._ignore_outgoing:
                    skip = True

            if not skip:

                name_string = ""
                if contact_name:
                    name_string = '[[contact:' + contact_name + '][' + contact_name + ']]'
                else:
                    name_string = "Unknown"
                output += name_string + ": "

                #if sms_subject != "null":
                    # in case of MMS we have a subject
                #    output += sms_subject
                #    notes = sms_body
                #else:
                #    output += sms_body
                #    notes = ""

                notes = sms_body

                timestamp = OrgFormat.datetime(time.gmtime(sms_date))
                data_for_hashing = output + timestamp + notes
                properties = OrgProperties(data_for_hashing=data_for_hashing)

                properties.add("NUMBER", sms_address)
                properties.add("NAME", contact_name)
                properties.add("SMS_SERVICE_CENTER", sms_service_center)
                properties.add("TIME", sms_time)

                self._writer.write_org_subitem(output=output,
                                               timestamp=timestamp,
                                               note=notes,
                                               properties=properties)


class SmsSuperBackupMemacs(Memacs):
    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        self._parser.add_argument(
            "-f", "--file", dest="smsxmlfile",
            action="store", required=True,
            help="path to sms xml backup file")

        self._parser.add_argument(
            "--ignore-incoming", dest="ignore_incoming",
            action="store_true",
            help="ignore incoming smses")

        self._parser.add_argument(
            "--ignore-outgoing", dest="ignore_outgoing",
            action="store_true",
            help="ignore outgoing smses")

    def _parser_parse_args(self):
        """
        overwritten method of class Memacs

        all additional arguments are parsed in here
        """
        Memacs._parser_parse_args(self)
        if not (os.path.exists(self._args.smsxmlfile) or \
                     os.access(self._args.smsxmlfile, os.R_OK)):
            self._parser.error("input file not found or not readable")

    def _main(self):
        """
        get's automatically called from Memacs class
        read the lines from sms backup xml file,
        parse and write them to org file
        """

        data = CommonReader.get_data_from_file(self._args.smsxmlfile)

        try:
            xml.sax.parseString(data.encode('utf-8'),
                                SmsSaxHandler(self._writer,
                                              self._args.ignore_incoming,
                                              self._args.ignore_outgoing))
        except SAXParseException:
            logging.error("No correct XML given")
            sys.exit(1)

########NEW FILE########
__FILENAME__ = svn
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2011-10-28 15:13:31 aw>

import sys
import os
import logging
import xml.sax
from xml.sax._exceptions import SAXParseException
from lib.orgproperty import OrgProperties
from lib.orgformat import OrgFormat
from lib.memacs import Memacs
from lib.reader import CommonReader


class SvnSaxHandler(xml.sax.handler.ContentHandler):
    """
    Sax handler for following xml's:

    <?xml version="1.0"?>
    <log>
    <logentry
       revision="13">
    <author>bob</author>
    <date>2011-11-05T18:18:22.936127Z</date>
    <msg>Bugfix.</msg>
    </logentry>
    </log>
    """

    def __init__(self, writer, grepauthor):
        """
        Ctor

        @param writer: orgwriter
        """
        self.__reset()
        self._writer = writer
        self.__grepauthor = grepauthor

    def __reset(self):
        """
        resets all variables
        """
        self.__author = ""
        self.__date = ""
        self.__msg = ""
        self.__rev = -1
        self.__on_node_name = ""  # used to store on which element we are
        self.__id_prefix = "rev-"

    def __write(self):
        """
        write attributes to writer (make an org_sub_item)
        """
        logging.debug("msg:%s", self.__msg)
        self.__msg = self.__msg.splitlines()
        subject = ""
        notes = ""

        # idea: look for the first -nonempty- message
        if len(self.__msg) > 0:
            start_notes = 0
            for i in range(len(self.__msg)):
                if self.__msg[i].strip() != "":
                    subject = self.__msg[i].strip()
                    start_notes = i + 1
                    break

            if len(self.__msg) > start_notes:
                for n in self.__msg[start_notes:]:
                    if n != "":
                        notes += n + "\n"

        output = "%s (r%d): %s" % (self.__author, self.__rev, subject)

        properties = OrgProperties(data_for_hashing=self.__author + subject)
        timestamp = OrgFormat.datetime(
            OrgFormat.datetupelutctimestamp(self.__date))
        properties.add("REVISION", self.__rev)

        if self.__grepauthor == None or \
        (self.__author.strip() == self.__grepauthor.strip()):
            self._writer.write_org_subitem(output=output,
                                           timestamp=timestamp,
                                           note=notes,
                                           properties=properties)

    def characters(self, content):
        """
        handles xml tags:
        - <author/>
        - <date/>
        - <msg/>

        and set those attributes
        """
        logging.debug("Handler @characters @%s , content=%s",
                      self.__on_node_name, content)
        if self.__on_node_name == "author":
            self.__author += content
        elif self.__on_node_name == "date":
            self.__date += content
        elif self.__on_node_name == "msg":
            self.__msg += content

    def startElement(self, name, attrs):
        """
        at every <tag> remember the tagname
        * sets the revision when in tag "logentry"
        """
        logging.debug("Handler @startElement name=%s,attrs=%s", name, attrs)

        if name == "logentry":
            self.__rev = int(attrs['revision'])

        self.__on_node_name = name

    def endElement(self, name):
        """
        at every </tag> clear the remembered tagname
        if we are at </logentry> then we can write a entry to stream
        """
        logging.debug("Handler @endElement name=%s", name)
        self.__on_node_name = ""
        if name == "logentry":
            self.__write()
            self.__reset()


class SvnMemacs(Memacs):
    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        self._parser.add_argument(
            "-f", "--file", dest="svnlogxmlfile",
            action="store",
            help="path to a an file which contains output from " + \
                " following svn command: svn log --xml")

        self._parser.add_argument(
           "-g", "--grep-author", dest="grepauthor",
           action="store",
           help="if you wanna parse only messages from a specific person. " + \
           "format:<author> of author to grep")

    def _parser_parse_args(self):
        """
        overwritten method of class Memacs

        all additional arguments are parsed in here
        """
        Memacs._parser_parse_args(self)
        if self._args.svnlogxmlfile and not \
                (os.path.exists(self._args.svnlogxmlfile) or \
                     os.access(self._args.svnlogxmlfile, os.R_OK)):
            self._parser.error("input file not found or not readable")

    def _main(self):
        """
        get's automatically called from Memacs class
        read the lines from svn xml file, parse and write them to org file
        """

        # read file
        if self._args.svnlogxmlfile:
            logging.debug("using as %s input_stream", self._args.svnlogxmlfile)
            data = CommonReader.get_data_from_file(self._args.svnlogxmlfile)
        else:
            logging.info("Using stdin as input_stream")
            data = CommonReader.get_data_from_stdin()

        try:
            xml.sax.parseString(data.encode('utf-8'),
                                SvnSaxHandler(self._writer,
                                              self._args.grepauthor))
        except SAXParseException:
            logging.error("No correct XML given")
            sys.exit(1)

########NEW FILE########
__FILENAME__ = csv_test
# -*- coding: utf-8 -*-
# Time-stamp: <2011-10-28 15:13:31 aw>

import unittest
import os
from memacs.csv import Csv


class TestCsv(unittest.TestCase):

    def setUp(self):
        pass

    def test_example1(self):
        example1 = os.path.dirname(os.path.abspath(__file__)) + \
        os.sep + "tmp" + os.sep + "example1.csv"

        argv = []
        argv.append("-f")
        argv.append(example1)
        argv.append("-ti")
        argv.append("5")
        argv.append("-tf")
        argv.append("%d.%m.%Y %H:%M:%S:%f")
        argv.append("-oi")
        argv.append("4 3 1")
        memacs = Csv(argv=argv)
        # or when in append mode:
        # memacs = Foo(argv=argv.split(), append=True)
        data = memacs.test_get_entries()

        # generate assertEquals :)
#        for d in range(len(data)):
#           print "self.assertEqual(\n\tdata[%d],\n\t\"%s\")" % \
#                (d, data[d])

        self.assertEqual(
            data[0],
            "** <2012-02-23 Thu 14:40:59> EUR 100,00 Amazon")
        self.assertEqual(
            data[1],
            "   :PROPERTIES:")
        self.assertEqual(
            data[2],
            "   :ID:         5526fcec678ca1dea255b60177e5daaa737d3805")
        self.assertEqual(
            data[3],
            "   :END:")

    def test_example2_delimiter(self):
        example1 = os.path.dirname(os.path.abspath(__file__)) + \
        os.sep + "tmp" + os.sep + "example2.csv"

        argv = []
        argv.append("--delimiter")
        argv.append("|")
        argv.append("-f")
        argv.append(example1)
        argv.append("-ti")
        argv.append("5")
        argv.append("-tf")
        argv.append("%d.%m.%Y %H:%M:%S:%f")
        argv.append("-oi")
        argv.append("4 3 1")
        memacs = Csv(argv=argv)
        # or when in append mode:
        # memacs = Foo(argv=argv.split(), append=True)
        data = memacs.test_get_entries()

        # generate assertEquals :)
#        for d in range(len(data)):
#           print "self.assertEqual(\n\tdata[%d],\n\t\"%s\")" % \
#                (d, data[d])

        self.assertEqual(
            data[0],
            "** <2012-02-23 Thu 14:40:59> EUR 100,00 Amazon")
        self.assertEqual(
            data[1],
            "   :PROPERTIES:")
        self.assertEqual(
            data[2],
            "   :ID:         5526fcec678ca1dea255b60177e5daaa737d3805")
        self.assertEqual(
            data[3],
            "   :END:")

    def tearDown(self):
        pass

########NEW FILE########
__FILENAME__ = example_test
# -*- coding: utf-8 -*-
# Time-stamp: <2011-10-28 15:13:31 aw>

import unittest
from memacs.example import Foo


class TestFoo(unittest.TestCase):

    def setUp(self):
        pass

    def test_all(self):
        argv = "-s"
        memacs = Foo(argv=argv.split())
        # or when in append mode:
        # memacs = Foo(argv=argv.split(), append=True)
        data = memacs.test_get_entries()

        # generate assertEquals :)
        #for d in range(len(data)):
        #   print "self.assertEqual(\n\tdata[%d],\n\t\"%s\")" % \
        #        (d, data[d])

        self.assertEqual(
            data[0],
            "** <1970-01-01 Thu 00:00> foo")
        self.assertEqual(
            data[1],
            "   :PROPERTIES:")
        self.assertEqual(
            data[2],
            "   :ID:         e7663db158b7ba301fb23e3dc40347970c7f8a0f")
        self.assertEqual(
            data[3],
            "   :END:")
        self.assertEqual(
            data[4],
            "** <1970-01-01 Thu 00:00> bar\t:tag1:tag2:")
        self.assertEqual(
            data[5],
            "   bar notes")
        self.assertEqual(
            data[6],
            "   foo notes")
        self.assertEqual(
            data[7],
            "   :PROPERTIES:")
        self.assertEqual(
            data[8],
            "   :DESCRIPTION:  foooo")
        self.assertEqual(
            data[9],
            "   :FOO-PROPERTY: asdf")
        self.assertEqual(
            data[10],
            "   :ID:           97521347348df02dab8bf86fbb6817c0af333a3f")
        self.assertEqual(
            data[11],
            "   :END:")

    def tearDown(self):
        pass

########NEW FILE########
__FILENAME__ = filenametimestamps_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2011-12-19 15:13:31 aw>

import unittest
import os
from memacs.filenametimestamps import FileNameTimeStamps


class TestFileNameTimeStamps(unittest.TestCase):

    def setUp(self):
        self.TMPFOLDER = os.path.normpath(
            os.path.dirname(os.path.abspath(__file__)) + os.path.sep + \
                "tmp") + os.path.sep
        if not os.path.exists(self.TMPFOLDER):
            os.makedirs(self.TMPFOLDER)

    def test_functional(self):
        tmpfile = self.TMPFOLDER + os.sep + '2011-12-19T23.59.12_test1.txt'
        entry = "** <2011-12-19 Mon 23:59:12> [[" + tmpfile + \
            "][2011-12-19T23.59.12_test1.txt]]"

        # touch file
        open(tmpfile, 'w').close()

        argv = "-s -f " + self.TMPFOLDER
        memacs = FileNameTimeStamps(argv=argv.split())
        data = memacs.test_get_entries()

        #for d in range(len(data)):
        #    print "self.assertEqual(\n\tdata[%d],\n\t\"%s\")" % \
        #        (d, data[d])

        self.assertEqual(
            data[0],
            entry)
        self.assertEqual(
            data[1],
            "   :PROPERTIES:")
        # id changes because data_for_hashing = link
        #self.assertEqual(
        #    data[2],
        #    "   :ID:             e3b38e22498caa8812c755ec20276714a1eb1919")
        self.assertEqual(
            data[3],
            "   :END:")

        os.remove(tmpfile)
        self.assertEqual(data[0], entry, "filenametimestamps - error")

########NEW FILE########
__FILENAME__ = git_test
# -*- coding: utf-8 -*-
# Time-stamp: <2011-10-28 15:13:31 aw>

import unittest
import os
from memacs.git import GitMemacs
from memacs.git import Commit


class TestCommit(unittest.TestCase):

    def test_ID_empty(self):
        c = Commit()
        self.assertTrue(c.is_empty())

    def test_ID(self):
        c = Commit()
        c.add_header("author Armin Wieser <armin.wieser" + \
                     "@example.com> 1324422878 +0100")
        c.add_body("i'm the subject")
        c.add_body("i'm in the body")

        output, properties, note, author, timestamp = c.get_output()
        self.assertEqual(output, "Armin Wieser: i'm the subject")
        self.assertEqual(note, "i'm in the body\n")
        self.assertEqual(author, "Armin Wieser")
        self.assertEqual(timestamp, "<2011-12-21 Wed 00:14:38>")

        #for p in unicode(properties).splitlines():
        #    print "\"" + p + "\\n\""
        p = "   :PROPERTIES:\n"
        p += "   :AUTHOR:     Armin Wieser <armin.wieser@example.com> " + \
        "1324422878 +0100\n"
        p += "   :ID:         2bcf0df19183b508b7d52e38ee1d811aabd207f5\n"
        p += "   :END:"

        self.assertEqual(unicode(properties), p)


class TestGitMemacs(unittest.TestCase):

    def setUp(self):
        self.test_file = os.path.dirname(os.path.abspath(__file__)) + \
            os.sep + "tmp" + os.sep + "git-rev-list-raw.txt"

    def test_from_file(self):
        argv = "-s -f " + self.test_file
        memacs = GitMemacs(argv=argv.split())
        data = memacs.test_get_entries()

        # generate assertEquals :)
        #for d in range(len(data)):
        #    print "self.assertEqual(\n\tdata[%d],\n\t \"%s\")" % \
        #       (d, data[d])
        self.assertEqual(
            data[0],
             "** <2011-11-19 Sat 11:50:55> Karl Voit:" + \
             " corrected cron-info for OS X")
        self.assertEqual(
            data[1],
             "   :PROPERTIES:")
        self.assertEqual(
            data[2],
             "   :COMMIT:     052ffa660ce1d8b0f9dd8f8fc794222e2463dce1")
        self.assertEqual(
            data[3],
             "   :TREE:       0c785721ff806d2570cb7d785adf294b0406609b")
        self.assertEqual(
            data[4],
             "   :COMMITTER:  Karl Voit <git@example.com> 1321699855" + \
             " +0100")
        self.assertEqual(
            data[5],
             "   :PARENT:     62f20271b87e8574370f1ded29938dad0313a399")
        self.assertEqual(
            data[6],
             "   :AUTHOR:     Karl Voit <git@example." + \
             "com> 1321699855 +0100")
        self.assertEqual(
            data[7],
             "   :ID:         11a9098b0a6cc0c979a7fce96b8e83baf5502bf8")
        self.assertEqual(
            data[8],
             "   :END:")
        self.assertEqual(
            data[9],
             "** <2011-11-19 Sat 11:50:30> Karl Voit: added RSS " + \
             "module description")
        self.assertEqual(
            data[10],
             "   :PROPERTIES:")
        self.assertEqual(
            data[11],
             "   :COMMIT:     62f20271b87e8574370f1ded29938dad0313a399")
        self.assertEqual(
            data[12],
             "   :TREE:       906b8b7e4bfd08850aef8c15b0fc4d5f6e9cc9a7")
        self.assertEqual(
            data[13],
             "   :COMMITTER:  Karl Voit <git@example.c" + \
             "om> 1321699830 +0100")
        self.assertEqual(
            data[14],
             "   :PARENT:     638e81c55daf0a69c78cc3af23a9e451ccea44ab")
        self.assertEqual(
            data[15],
             "   :AUTHOR:     Karl Voit <git@example.com> 132" + \
             "1699830 +0100")
        self.assertEqual(
            data[16],
             "   :ID:         dce2f11c7c495885f65b650b29a09cb88cb52acf")
        self.assertEqual(
            data[17],
             "   :END:")
        self.assertEqual(
            data[18],
             "** <2011-11-02 Wed 22:46:06> Armin Wieser: add" + \
             "ed Orgformate.date()")
        self.assertEqual(
            data[19],
             "   :PROPERTIES:")
        self.assertEqual(
            data[20],
             "   :COMMITTER:     Armin Wieser <armin.wieser@" + \
             "example.com> 1320270366 +0100")
        self.assertEqual(
            data[21],
             "   :PARENT:        7ddaa9839611662c5c0dbf2bb2740e362ae4d566")
        self.assertEqual(
            data[22],
             "   :AUTHOR:        Armin Wieser <armin.wieser@ex" + \
             "ample.com> 1320270366 +0100")
        self.assertEqual(
            data[23],
             "   :TREE:          2d440e6b42b917e9a69d5283b9d1ed4a77797ee9")
        self.assertEqual(
            data[24],
             "   :SIGNED-OFF-BY: Armin Wieser <armin.wieser@example.com>")
        self.assertEqual(
            data[25],
             "   :COMMIT:        9b4523b2c4542349e8b4ca3ca595701a50b3c315")
        self.assertEqual(
            data[26],
             "   :ID:            82c0a5afd67557b85870efdd5da6411b5014e26c")
        self.assertEqual(
            data[27],
             "   :END:")
        self.assertEqual(
            data[28],
             "** <2011-11-02 Wed 19:58:32> Armin Wieser: orgf" + \
             "ormat added for orgmode-syntax")
        self.assertEqual(
            data[29],
             "   :PROPERTIES:")
        self.assertEqual(
            data[30],
             "   :COMMITTER:     Armin Wieser <armin.wieser@e" + \
             "xample.com> 1320260312 +0100")
        self.assertEqual(
            data[31],
             "   :PARENT:        f845d8c1f1a4194e3b27b5bf39bac1b30bd095f6")
        self.assertEqual(
            data[32],
             "   :AUTHOR:        Armin Wieser <armin.wieser@" + \
             "example.com> 1320260312 +0100")
        self.assertEqual(
            data[33],
             "   :TREE:          663a7c370b985f3b7e9794dec07f28d4e6ff3936")
        self.assertEqual(
            data[34],
             "   :SIGNED-OFF-BY: Armin Wieser <armin.wieser@example.com>")
        self.assertEqual(
            data[35],
             "   :COMMIT:        7ddaa9839611662c5c0dbf2bb2740e362ae4d566")
        self.assertEqual(
            data[36],
             "   :ID:            0594d8f7184c60e3e364ec34e64aa42e9837919c")
        self.assertEqual(
            data[37],
             "   :END:")

    def test_number_entries_all(self):
        argv = "-s -f " + self.test_file
        memacs = GitMemacs(argv=argv.split())
        data = memacs.test_get_entries()
        self.assertEqual(len(data), 109)  # 109 lines in sum

    def test_number_entries_grep(self):
        argv = '-s -f ' + self.test_file
        argv = argv.split()
        argv.append("-g")
        argv.append("Armin Wieser")
        memacs = GitMemacs(argv=argv)
        data = memacs.test_get_entries()
        self.assertEqual(len(data), 91)  # 91 lines from Armin Wieser

########NEW FILE########
__FILENAME__ = ical_test
# -*- coding: utf-8 -*-
# Time-stamp: <2011-10-28 15:13:31 aw>

import unittest
import os
from memacs.ical import CalendarMemacs


class TestCalendar(unittest.TestCase):

    def test_all(self):
        test_file = os.path.dirname(os.path.abspath(__file__)) + \
        os.sep + "tmp" + os.sep + "austrian_holidays_from_google.ics"
        argv = "-s -cf " + test_file
        memacs = CalendarMemacs(argv=argv.split())
        data = memacs.test_get_entries()
        #for d in range(len(data)):
        #      print "self.assertEqual(\n\tdata[%d],\n\t \"%s\")" % \
        #            (d, data[d])

        self.assertEqual(
            data[0],
             "** <2012-05-28 Mon>--<2012-05-28 Mon> Whit Monday")
        self.assertEqual(
            data[1],
             "   :PROPERTIES:")
        self.assertEqual(
            data[2],
             "   :ID:         b6972cddd864a2fba79ed8ff95e0f2f8948f2410")
        self.assertEqual(
            data[3],
             "   :END:")
        self.assertEqual(
            data[4],
             "** <2011-02-14 Mon>--<2011-02-14 Mon> Valentine's day")
        self.assertEqual(
            data[5],
             "   :PROPERTIES:")
        self.assertEqual(
            data[6],
             "   :ID:         66186caf3409e2086a9c199a03cb6ff440ab738b")
        self.assertEqual(
            data[7],
             "   :END:")
        self.assertEqual(
            data[8],
             "** <2010-02-14 Sun>--<2010-02-14 Sun> Valentine's day")
        self.assertEqual(
            data[9],
             "   :PROPERTIES:")
        self.assertEqual(
            data[10],
             "   :ID:         bee25809ac0695d567664decb61592ada965f858")
        self.assertEqual(
            data[11],
             "   :END:")
        self.assertEqual(
            data[12],
             "** <2012-02-14 Tue>--<2012-02-14 Tue> Valentine's day")
        self.assertEqual(
            data[13],
             "   :PROPERTIES:")
        self.assertEqual(
            data[14],
             "   :ID:         d74b79979f616f13715439a1ef7e0b2f0c69f220")
        self.assertEqual(
            data[15],
             "   :END:")
        self.assertEqual(
            data[16],
             "** <2012-12-26 Wed>--<2012-12-26 Wed> St. Stephan's Day")
        self.assertEqual(
            data[17],
             "   :PROPERTIES:")
        self.assertEqual(
            data[18],
             "   :ID:         c2559692c5465c6dad0f014f936eef320b516b9f")
        self.assertEqual(
            data[19],
             "   :END:")
        self.assertEqual(
            data[20],
             "** <2010-12-26 Sun>--<2010-12-26 Sun> St. Stephan's Day")
        self.assertEqual(
            data[21],
             "   :PROPERTIES:")
        self.assertEqual(
            data[22],
             "   :ID:         c145ba3f76fab2f9eca5a9b09695c47b1f65554a")
        self.assertEqual(
            data[23],
             "   :END:")
        self.assertEqual(
            data[24],
             "** <2011-12-26 Mon>--<2011-12-26 Mon> St. Stephan's Day")
        self.assertEqual(
            data[25],
             "   :PROPERTIES:")
        self.assertEqual(
            data[26],
             "   :ID:         0c663e887265d372cf40d3c7f1d7fd595a0114a0")
        self.assertEqual(
            data[27],
             "   :END:")
        self.assertEqual(
            data[28],
             "** <2011-12-06 Tue>--<2011-12-06 Tue> St. Nicholas")
        self.assertEqual(
            data[29],
             "   :PROPERTIES:")
        self.assertEqual(
            data[30],
             "   :ID:         821d4ce5231db9f037cf64f8b3cfeeeb65c84bee")
        self.assertEqual(
            data[31],
             "   :END:")
        self.assertEqual(
            data[32],
             "** <2010-12-06 Mon>--<2010-12-06 Mon> St. Nicholas")
        self.assertEqual(
            data[33],
             "   :PROPERTIES:")
        self.assertEqual(
            data[34],
             "   :ID:         4b1f7183ef085af82ec9b7be7845d35d9504b0b6")
        self.assertEqual(
            data[35],
             "   :END:")
        self.assertEqual(
            data[36],
             "** <2012-12-06 Thu>--<2012-12-06 Thu> St. Nicholas")
        self.assertEqual(
            data[37],
             "   :PROPERTIES:")
        self.assertEqual(
            data[38],
             "   :ID:         34c1c44697bedbe3228842204e84f45ec45b0923")
        self.assertEqual(
            data[39],
             "   :END:")
        self.assertEqual(
            data[40],
             "** <2011-12-31 Sat>--<2011-12-31 Sat> New Year's Eve")
        self.assertEqual(
            data[41],
             "   :PROPERTIES:")
        self.assertEqual(
            data[42],
             "   :ID:         ea722a9d474e8bbda41f48460ad3681e10097044")
        self.assertEqual(
            data[43],
             "   :END:")
        self.assertEqual(
            data[44],
             "** <2010-12-31 Fri>--<2010-12-31 Fri> New Year's Eve")
        self.assertEqual(
            data[45],
             "   :PROPERTIES:")
        self.assertEqual(
            data[46],
             "   :ID:         afcbb4912aaede6e31b0c4bdb9221b90f10c1b62")
        self.assertEqual(
            data[47],
             "   :END:")
        self.assertEqual(
            data[48],
             "** <2012-01-01 Sun>--<2012-01-01 Sun> New Year")
        self.assertEqual(
            data[49],
             "   :PROPERTIES:")
        self.assertEqual(
            data[50],
             "   :ID:         9a533328738c914dcc4abd5bb571e63cccae0fa2")
        self.assertEqual(
            data[51],
             "   :END:")
        self.assertEqual(
            data[52],
             "** <2010-01-01 Fri>--<2010-01-01 Fri> New Year")
        self.assertEqual(
            data[53],
             "   :PROPERTIES:")
        self.assertEqual(
            data[54],
             "   :ID:         1239f768e303f38b312d4fa84ad295f44a12ea99")
        self.assertEqual(
            data[55],
             "   :END:")
        self.assertEqual(
            data[56],
             "** <2011-01-01 Sat>--<2011-01-01 Sat> New Year")
        self.assertEqual(
            data[57],
             "   :PROPERTIES:")
        self.assertEqual(
            data[58],
             "   :ID:         c578509791f5865707d0018ad79c2eaf37210481")
        self.assertEqual(
            data[59],
             "   :END:")
        self.assertEqual(
            data[60],
             "** <2010-10-26 Tue>--<2010-10-26 Tue> National Holiday")
        self.assertEqual(
            data[61],
             "   :PROPERTIES:")
        self.assertEqual(
            data[62],
             "   :ID:         dffe086b45549c333b308892bf7b4b83485ea216")
        self.assertEqual(
            data[63],
             "   :END:")
        self.assertEqual(
            data[64],
             "** <2012-10-26 Fri>--<2012-10-26 Fri> National Holiday")
        self.assertEqual(
            data[65],
             "   :PROPERTIES:")
        self.assertEqual(
            data[66],
             "   :ID:         5d74bcc91609435775c774cf4b2c373e3b6b9a9e")
        self.assertEqual(
            data[67],
             "   :END:")
        self.assertEqual(
            data[68],
             "** <2011-10-26 Wed>--<2011-10-26 Wed> National Holiday")
        self.assertEqual(
            data[69],
             "   :PROPERTIES:")
        self.assertEqual(
            data[70],
             "   :ID:         5c99d7709dfe1e81b18e3c3343e06edd0854015f")
        self.assertEqual(
            data[71],
             "   :END:")
        self.assertEqual(
            data[72],
             "** <2011-05-01 Sun>--<2011-05-01 Sun> Labour Day")
        self.assertEqual(
            data[73],
             "   :PROPERTIES:")
        self.assertEqual(
            data[74],
             "   :ID:         5f18bf2bffdedf1fd50bca2b5ccfb8bd7554b52f")
        self.assertEqual(
            data[75],
             "   :END:")
        self.assertEqual(
            data[76],
             "** <2010-05-01 Sat>--<2010-05-01 Sat> Labour Day")
        self.assertEqual(
            data[77],
             "   :PROPERTIES:")
        self.assertEqual(
            data[78],
             "   :ID:         248bbd02f36ba32fbe36c5fdf65ab66a400307c5")
        self.assertEqual(
            data[79],
             "   :END:")
        self.assertEqual(
            data[80],
             "** <2012-05-01 Tue>--<2012-05-01 Tue> Labour Day")
        self.assertEqual(
            data[81],
             "   :PROPERTIES:")
        self.assertEqual(
            data[82],
             "   :ID:         709d57b34901a8dab5277cdec884acb989579451")
        self.assertEqual(
            data[83],
             "   :END:")
        self.assertEqual(
            data[84],
             "** <2012-12-08 Sat>--<2012-12-08 Sat> Immaculate Conception")
        self.assertEqual(
            data[85],
             "   :PROPERTIES:")
        self.assertEqual(
            data[86],
             "   :ID:         9718f2c669addc152c80d478beaeb81ab7dc2757")
        self.assertEqual(
            data[87],
             "   :END:")
        self.assertEqual(
            data[88],
             "** <2010-12-08 Wed>--<2010-12-08 Wed> Immaculate Conception")
        self.assertEqual(
            data[89],
             "   :PROPERTIES:")
        self.assertEqual(
            data[90],
             "   :ID:         7d02e0af4e44664e5a474376dd97ba838bcdb725")
        self.assertEqual(
            data[91],
             "   :END:")
        self.assertEqual(
            data[92],
             "** <2011-12-08 Thu>--<2011-12-08 Thu> Immaculate Conception")
        self.assertEqual(
            data[93],
             "   :PROPERTIES:")
        self.assertEqual(
            data[94],
             "   :ID:         20e022ce71904efac1f90d45b24b4164623a919b")
        self.assertEqual(
            data[95],
             "   :END:")
        self.assertEqual(
            data[96],
             "** <2012-04-06 Fri>--<2012-04-06 Fri> Good Friday")
        self.assertEqual(
            data[97],
             "   :PROPERTIES:")
        self.assertEqual(
            data[98],
             "   :ID:         6a9a405cdba496987ca9ab66aef623fe0ed70e26")
        self.assertEqual(
            data[99],
             "   :END:")
        self.assertEqual(
            data[100],
             "** <2010-01-06 Wed>--<2010-01-06 Wed> Epiphany")
        self.assertEqual(
            data[101],
             "   :PROPERTIES:")
        self.assertEqual(
            data[102],
             "   :ID:         6640ef7807da042944392601c4e9b046174bce8e")
        self.assertEqual(
            data[103],
             "   :END:")
        self.assertEqual(
            data[104],
             "** <2012-01-06 Fri>--<2012-01-06 Fri> Epiphany")
        self.assertEqual(
            data[105],
             "   :PROPERTIES:")
        self.assertEqual(
            data[106],
             "   :ID:         0aa9ab88fb1bfcb9b0fb430e673ec23eb42a4f38")
        self.assertEqual(
            data[107],
             "   :END:")
        self.assertEqual(
            data[108],
             "** <2011-01-06 Thu>--<2011-01-06 Thu> Epiphany")
        self.assertEqual(
            data[109],
             "   :PROPERTIES:")
        self.assertEqual(
            data[110],
             "   :ID:         36897fcbb92a331ebebb86f4cef7b0e988c020c6")
        self.assertEqual(
            data[111],
             "   :END:")
        self.assertEqual(
            data[112],
             "** <2012-04-09 Mon>--<2012-04-09 Mon> Easter Monday")
        self.assertEqual(
            data[113],
             "   :PROPERTIES:")
        self.assertEqual(
            data[114],
             "   :ID:         a71164883dcb44825f7de50f68b7ea881b1a5d23")
        self.assertEqual(
            data[115],
             "   :END:")
        self.assertEqual(
            data[116],
             "** <2012-04-08 Sun>--<2012-04-08 Sun> Easter")
        self.assertEqual(
            data[117],
             "   :PROPERTIES:")
        self.assertEqual(
            data[118],
             "   :ID:         7dcfbb563cd9300bf18f3c05965a1b0c7c6442b8")
        self.assertEqual(
            data[119],
             "   :END:")
        self.assertEqual(
            data[120],
             "** <2012-06-07 Thu>--<2012-06-07 Thu> Corpus Christi")
        self.assertEqual(
            data[121],
             "   :PROPERTIES:")
        self.assertEqual(
            data[122],
             "   :ID:         01cd602579e0774b020c3d13a760e8fa828c6aec")
        self.assertEqual(
            data[123],
             "   :END:")
        self.assertEqual(
            data[124],
             "** <2011-12-24 Sat>--<2011-12-24 Sat> Christmas Eve")
        self.assertEqual(
            data[125],
             "   :PROPERTIES:")
        self.assertEqual(
            data[126],
             "   :ID:         4b91f8eefc9723bb3022b2bedb4c4d098f7f9d39")
        self.assertEqual(
            data[127],
             "   :END:")
        self.assertEqual(
            data[128],
             "** <2010-12-24 Fri>--<2010-12-24 Fri> Christmas Eve")
        self.assertEqual(
            data[129],
             "   :PROPERTIES:")
        self.assertEqual(
            data[130],
             "   :ID:         b3b00147203e50aa69fdae2f6745b78d13a39231")
        self.assertEqual(
            data[131],
             "   :END:")
        self.assertEqual(
            data[132],
             "** <2012-12-24 Mon>--<2012-12-24 Mon> Christmas Eve")
        self.assertEqual(
            data[133],
             "   :PROPERTIES:")
        self.assertEqual(
            data[134],
             "   :ID:         23506451af37175457bfff7b113aff5ff75881e7")
        self.assertEqual(
            data[135],
             "   :END:")
        self.assertEqual(
            data[136],
             "** <2010-12-25 Sat>--<2010-12-25 Sat> Christmas")
        self.assertEqual(
            data[137],
             "   :PROPERTIES:")
        self.assertEqual(
            data[138],
             "   :ID:         ae52748d82d25b1ada9ef73e6c608519c0cecca5")
        self.assertEqual(
            data[139],
             "   :END:")
        self.assertEqual(
            data[140],
             "** <2011-12-25 Sun>--<2011-12-25 Sun> Christmas")
        self.assertEqual(
            data[141],
             "   :PROPERTIES:")
        self.assertEqual(
            data[142],
             "   :ID:         802fb8acb3618909a6d7aaf605bf732a97a84d39")
        self.assertEqual(
            data[143],
             "   :END:")
        self.assertEqual(
            data[144],
             "** <2012-12-25 Tue>--<2012-12-25 Tue> Christmas")
        self.assertEqual(
            data[145],
             "   :PROPERTIES:")
        self.assertEqual(
            data[146],
             "   :ID:         1dc9ebe2f8ff2c91ca155c30ae65a67db11cf8aa")
        self.assertEqual(
            data[147],
             "   :END:")
        self.assertEqual(
            data[148],
             "** <2010-08-15 Sun>--<2010-08-15 Sun> Assumption")
        self.assertEqual(
            data[149],
             "   :PROPERTIES:")
        self.assertEqual(
            data[150],
             "   :ID:         c3e85e7c44c5cca95efa0751c7c52375640b43c2")
        self.assertEqual(
            data[151],
             "   :END:")
        self.assertEqual(
            data[152],
             "** <2012-08-15 Wed>--<2012-08-15 Wed> Assumption")
        self.assertEqual(
            data[153],
             "   :PROPERTIES:")
        self.assertEqual(
            data[154],
             "   :ID:         52c49d4ca2a196e6409ac362183cedcd656975ef")
        self.assertEqual(
            data[155],
             "   :END:")
        self.assertEqual(
            data[156],
             "** <2011-08-15 Mon>--<2011-08-15 Mon> Assumption")
        self.assertEqual(
            data[157],
             "   :PROPERTIES:")
        self.assertEqual(
            data[158],
             "   :ID:         be957e5083131794b874b06597cd1cc935d35408")
        self.assertEqual(
            data[159],
             "   :END:")
        self.assertEqual(
            data[160],
             "** <2012-05-17 Thu>--<2012-05-17 Thu> Ascension Day")
        self.assertEqual(
            data[161],
             "   :PROPERTIES:")
        self.assertEqual(
            data[162],
             "   :ID:         f718e41128812a9864df1a1aa649c23c82f453f9")
        self.assertEqual(
            data[163],
             "   :END:")
        self.assertEqual(
            data[164],
             "** <2011-11-02 Wed>--<2011-11-02 Wed> All Souls' Day")
        self.assertEqual(
            data[165],
             "   :PROPERTIES:")
        self.assertEqual(
            data[166],
             "   :ID:         f55d246b411fd4fe3d47205041538d04f56cac53")
        self.assertEqual(
            data[167],
             "   :END:")
        self.assertEqual(
            data[168],
             "** <2010-11-02 Tue>--<2010-11-02 Tue> All Souls' Day")
        self.assertEqual(
            data[169],
             "   :PROPERTIES:")
        self.assertEqual(
            data[170],
             "   :ID:         62e1a6c16ce2c40e33d67961b6cec5c0a099b14d")
        self.assertEqual(
            data[171],
             "   :END:")
        self.assertEqual(
            data[172],
             "** <2012-11-02 Fri>--<2012-11-02 Fri> All Souls' Day")
        self.assertEqual(
            data[173],
             "   :PROPERTIES:")
        self.assertEqual(
            data[174],
             "   :ID:         c9eae72e34489720698a1054cd03bb4cc8859e71")
        self.assertEqual(
            data[175],
             "   :END:")
        self.assertEqual(
            data[176],
             "** <2010-11-01 Mon>--<2010-11-01 Mon> All Saints' Day")
        self.assertEqual(
            data[177],
             "   :PROPERTIES:")
        self.assertEqual(
            data[178],
             "   :ID:         b87bcffe87fda005047d738c07a31cd8c25f609c")
        self.assertEqual(
            data[179],
             "   :END:")
        self.assertEqual(
            data[180],
             "** <2012-11-01 Thu>--<2012-11-01 Thu> All Saints' Day")
        self.assertEqual(
            data[181],
             "   :PROPERTIES:")
        self.assertEqual(
            data[182],
             "   :ID:         37b17e9da936c61a627101afd0cc87d28aafbe70")
        self.assertEqual(
            data[183],
             "   :END:")
        self.assertEqual(
            data[184],
             "** <2011-11-01 Tue>--<2011-11-01 Tue> All Saints' Day")
        self.assertEqual(
            data[185],
             "   :PROPERTIES:")
        self.assertEqual(
            data[186],
             "   :ID:         fe605142ace6ab6268fc672fccece05219c17148")
        self.assertEqual(
            data[187],
             "   :END:")

########NEW FILE########
__FILENAME__ = orgformat_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-09-28 13:02:55 vk>

import unittest
import time
import datetime
from memacs.lib.orgformat import OrgFormat
from memacs.lib.orgformat import TimestampParseException

class TestOrgFormat(unittest.TestCase):

    ## FIXXME: (Note) These test are *not* exhaustive unit tests. They only 
    ##         show the usage of the methods. Please add "mean" test cases and
    ##         borderline cases!

    def setUp(self):
        pass

    def test_all(self):

        self.assertEqual(
            "foo",
            "foo")

    def test_link(self):

        self.assertEqual(
            OrgFormat.link("http://github.org/novoid/memacs"),
            u'[[http://github.org/novoid/memacs]]')

        self.assertEqual(
            OrgFormat.link("http://github.org/novoid/memacs with space"),
            u'[[http://github.org/novoid/memacs%20with%20space]]')

        self.assertEqual(
            OrgFormat.link("http://github.org/novoid/memacs", "Memacs Repository"),
            u'[[http://github.org/novoid/memacs][Memacs Repository]]')


    def test_date(self):

        ## fixed day:
        self.assertEqual(
            OrgFormat.date(time.struct_time([1980,12,31,0,0,0,0,0,0])),
            u'<1980-12-31 Wed>' )
        
        ## fixed time with seconds:
        self.assertEqual(
            OrgFormat.date(time.struct_time([1980,12,31,23,59,58,0,0,0]), 'foo'),
            u'<1980-12-31 Wed 23:59>' )  ## seconds are not (yet) defined in Org-mode

        ## fixed time without seconds:
        self.assertEqual(
            OrgFormat.date(time.struct_time([1980,12,31,23,59,0,0,0,0]), 'foo'),
            u'<1980-12-31 Wed 23:59>' )

        YYYYMMDDwday = time.strftime('%Y-%m-%d %a', time.localtime())
        hhmmss = time.strftime('%H:%M', time.localtime())  ## seconds are not (yet) defined in Org-mode

        ## simple form with current day:
        self.assertEqual(
            OrgFormat.date(time.localtime()),
            u'<' + YYYYMMDDwday + u'>' )
        
        ## show_time parameter not named:
        self.assertEqual(
            OrgFormat.date(time.localtime(), True),
            u'<' + YYYYMMDDwday + u' ' + hhmmss + u'>' )
        
        ## show_time parameter named:
        self.assertEqual(
            OrgFormat.date(time.localtime(), show_time=True),
            u'<' + YYYYMMDDwday + u' ' + hhmmss + u'>' )
        

    def test_inactive_date(self):

        ## fixed day:
        self.assertEqual(
            OrgFormat.inactive_date(time.struct_time([1980,12,31,0,0,0,0,0,0])),
            u'[1980-12-31 Wed]' )
        
        ## fixed time with seconds:
        self.assertEqual(
            OrgFormat.inactive_date(time.struct_time([1980,12,31,23,59,58,0,0,0]), 'foo'),
            u'[1980-12-31 Wed 23:59]' )  ## seconds are not (yet) defined in Org-mode

        ## fixed time without seconds:
        self.assertEqual(
            OrgFormat.inactive_date(time.struct_time([1980,12,31,23,59,0,0,0,0]), 'foo'),
            u'[1980-12-31 Wed 23:59]' )

        YYYYMMDDwday = time.strftime('%Y-%m-%d %a', time.localtime())
        hhmmss = time.strftime('%H:%M', time.localtime())  ## seconds are not (yet) defined in Org-mode

        ## simple form with current day:
        self.assertEqual(
            OrgFormat.inactive_date(time.localtime()),
            u'[' + YYYYMMDDwday + u']' )
        
        ## show_time parameter not named:
        self.assertEqual(
            OrgFormat.inactive_date(time.localtime(), True),
            u'[' + YYYYMMDDwday + u' ' + hhmmss + u']' )
        
        ## show_time parameter named:
        self.assertEqual(
            OrgFormat.inactive_date(time.localtime(), show_time=True),
            u'[' + YYYYMMDDwday + u' ' + hhmmss + u']' )
        

    def test_datetime(self):

        ## fixed time with seconds:
        self.assertEqual(
            OrgFormat.datetime(time.struct_time([1980,12,31,23,59,58,0,0,0])),
            u'<1980-12-31 Wed 23:59>' )  ## seconds are not (yet) defined in Org-mode

        ## fixed time without seconds:
        self.assertEqual(
            OrgFormat.datetime(time.struct_time([1980,12,31,23,59,0,0,0,0])),
            u'<1980-12-31 Wed 23:59>' )

        YYYYMMDDwday = time.strftime('%Y-%m-%d %a', time.localtime())
        hhmmss = time.strftime('%H:%M', time.localtime())  ## seconds are not (yet) defined in Org-mode

        ## show_time parameter not named:
        self.assertEqual(
            OrgFormat.datetime(time.localtime()),
            u'<' + YYYYMMDDwday + u' ' + hhmmss + u'>' )
        
        ## show_time parameter named:
        self.assertEqual(
            OrgFormat.datetime(time.localtime()),
            u'<' + YYYYMMDDwday + u' ' + hhmmss + u'>' )
        

    def test_inactive_datetime(self):

        ## fixed time with seconds:
        self.assertEqual(
            OrgFormat.inactive_datetime(time.struct_time([1980,12,31,23,59,58,0,0,0])),
            u'[1980-12-31 Wed 23:59]' )  ## seconds are not (yet) defined in Org-mode

        ## fixed time without seconds:
        self.assertEqual(
            OrgFormat.inactive_datetime(time.struct_time([1980,12,31,23,59,0,0,0,0])),
            u'[1980-12-31 Wed 23:59]' )

        YYYYMMDDwday = time.strftime('%Y-%m-%d %a', time.localtime())
        hhmmss = time.strftime('%H:%M', time.localtime())  ## seconds are not (yet) defined in Org-mode

        ## show_time parameter not named:
        self.assertEqual(
            OrgFormat.inactive_datetime(time.localtime()),
            u'[' + YYYYMMDDwday + u' ' + hhmmss + u']' )
        
        ## show_time parameter named:
        self.assertEqual(
            OrgFormat.inactive_datetime(time.localtime()),
            u'[' + YYYYMMDDwday + u' ' + hhmmss + u']' )

        
    def test_daterange(self):

        ## fixed time with seconds:
        self.assertEqual(
            OrgFormat.daterange(
                time.struct_time([1980,12,31,23,59,58,0,0,0]),
                time.struct_time([1981,1,15,15,30,02,0,0,0]),
                ),
            u'<1980-12-31 Wed>--<1981-01-15 Thu>' )

        ## provoke error:
        with self.assertRaises(AssertionError):
            OrgFormat.daterange('foo', 42)


    def test_datetimerange(self):

        self.assertEqual(
            OrgFormat.datetimerange(
                time.struct_time([1980,12,31,23,59,58,0,0,0]),
                time.struct_time([1981,1,15,15,30,02,0,0,0]),
                ),
            u'<1980-12-31 Wed 23:59>--<1981-01-15 Thu 15:30>' )  ## seconds are not (yet) defined in Org-mode

        self.assertEqual(
            OrgFormat.datetimerange(
                time.struct_time([1980,12,31,23,59,0,0,0,0]),
                time.struct_time([1981,1,15,15,30,02,0,0,0]),
                ),
            u'<1980-12-31 Wed 23:59>--<1981-01-15 Thu 15:30>' )


        self.assertEqual(
            OrgFormat.datetimerange(
                time.struct_time([1980,12,31,23,59,0,0,0,0]),
                time.struct_time([1981,1,15,15,30,0,0,0,0]),
                ),
            u'<1980-12-31 Wed 23:59>--<1981-01-15 Thu 15:30>' )


    def test_utcrange(self):

        self.assertEqual(
            OrgFormat.utcrange(
                time.struct_time([1980,12,31,23,59,58,0,0,0]),
                time.struct_time([1981,1,15,15,30,02,0,0,0]),
                ),
            OrgFormat.datetimerange(
                time.struct_time([1980,12,31,23,59,58,0,0,0]),
                time.struct_time([1981,1,15,15,30,02,0,0,0]),
                )
             )

        self.assertEqual(
            OrgFormat.utcrange(
                time.struct_time([1980,12,31,23,59,0,0,0,0]),
                time.struct_time([1981,1,15,15,30,02,0,0,0]),
                ),
            OrgFormat.datetimerange(
                time.struct_time([1980,12,31,23,59,0,0,0,0]),
                time.struct_time([1981,1,15,15,30,02,0,0,0]),
                )
            )

        self.assertEqual(
            OrgFormat.utcrange(
                time.struct_time([1980,12,31,0,0,0,0,0,0]),
                time.struct_time([1981,1,15,0,0,0,0,0,0]),
                ),
            OrgFormat.daterange(
                time.struct_time([1980,12,31,23,59,0,0,0,0]),
                time.struct_time([1981,1,15,15,30,02,0,0,0]),
                )
            )


    def test_strdate(self):

        self.assertEqual(
            OrgFormat.strdate('1980-12-31'),
            u'<1980-12-31 Wed>' )
        
        self.assertEqual(
            OrgFormat.strdate('1981-01-15'),
            u'<1981-01-15 Thu>' )

        self.assertEqual(
            OrgFormat.strdate('1980-12-31', False),
            u'<1980-12-31 Wed>' )
        
        self.assertEqual(
            OrgFormat.strdate('1981-01-15', False),
            u'<1981-01-15 Thu>' )

        self.assertEqual(
            OrgFormat.strdate('1980-12-31', True),
            u'[1980-12-31 Wed]' )
        
        self.assertEqual(
            OrgFormat.strdate('1981-01-15', True),
            u'[1981-01-15 Thu]' )

        with self.assertRaises(TimestampParseException):
            OrgFormat.strdate('1981-01-15foo'),
        

    def test_strdatetime(self):

        self.assertEqual(
            OrgFormat.strdatetime('1980-12-31 23:59'),
            u'<1980-12-31 Wed 23:59>' )
        
        self.assertEqual(
            OrgFormat.strdatetime('1981-01-15 15:10'),
            u'<1981-01-15 Thu 15:10>' )

        with self.assertRaises(TimestampParseException):
            OrgFormat.strdatetime('1981-01-15 15.10')

        with self.assertRaises(TimestampParseException):
            OrgFormat.strdatetime('1981-01-15T15:10')
        

    def test_strdatetimeiso8601(self):

        self.assertEqual(
            OrgFormat.strdatetimeiso8601('1980-12-31T23.59'),
            u'<1980-12-31 Wed 23:59>' )
        
        self.assertEqual(
            OrgFormat.strdatetimeiso8601('1981-01-15T15.10.23'),
            u'<1981-01-15 Thu 15:10>' )  ## seconds are not (yet) defined in Org-mode
        
        with self.assertRaises(TimestampParseException):
            OrgFormat.strdatetimeiso8601('1981-01-15T15:10')
        

    def test_datetimetupeliso8601(self):
        
        self.assertEqual(
            OrgFormat.datetimetupeliso8601('1980-12-31T23.59'),
            time.struct_time([1980, 12, 31, 
                             23, 59, 0, 
                             2, 366, -1]) )

        self.assertEqual(
            OrgFormat.datetimetupeliso8601('1980-12-31T23.59.58'),
            time.struct_time([1980, 12, 31, 
                             23, 59, 58, 
                             2, 366, -1]) )
    
        
    def test_datetupleiso8601(self):

        self.assertEqual(
            OrgFormat.datetupeliso8601('1980-12-31'),
            time.struct_time([1980, 12, 31, 
                             0, 0, 0, 
                             2, 366, -1]) )

        with self.assertRaises(TimestampParseException):
            OrgFormat.datetupeliso8601('1980-12-31T23.59'),
        
        
    def test_datetupelutctimestamp(self):

        self.assertEqual(
            OrgFormat.datetupelutctimestamp('19801231'),
            time.struct_time([1980, 12, 31, 
                             0, 0, 0, 
                             2, 366, -1]) )

        self.assertEqual(
            OrgFormat.datetupelutctimestamp('19801231T235958'),
            time.struct_time([1980, 12, 31, 
                             23, 59, 58, 
                             2, 366, -1]) )

        ## FIXXME: this is most likely time zone depending:
        # self.assertEqual(
        #     OrgFormat.datetupelutctimestamp('19801231T120000Z'),
        #     time.struct_time([1980, 12, 31, 
        #                      13, 00, 00, 
        #                      2, 366, 0]) )



    def test_contact_mail_mailto_link(self):

        self.assertEqual(
            OrgFormat.contact_mail_mailto_link("<bob.bobby@example.com>"),
            u"[[mailto:bob.bobby@example.com][bob.bobby@example.com]]" )

        self.assertEqual(
            OrgFormat.contact_mail_mailto_link("Bob Bobby <bob.bobby@example.com>"),
            u"[[mailto:bob.bobby@example.com][Bob Bobby]]" )


    def test_newsgroup_link(self):

        self.assertEqual(
            OrgFormat.newsgroup_link("foo"),
            u"[[news:foo][foo]]" )

        self.assertEqual(
            OrgFormat.newsgroup_link("foo.bar.baz"),
            u"[[news:foo.bar.baz][foo.bar.baz]]" )


    def test_orgmode_timestamp_to_datetime(self):

        self.assertEqual(
            OrgFormat.orgmode_timestamp_to_datetime(u"<1980-12-31 Wed 23:59>"),
            datetime.datetime(1980, 12, 31, 23, 59, 0))
        

    def test_apply_timedelta_to_Orgmode_timestamp(self):

        self.assertEqual(
            OrgFormat.apply_timedelta_to_Orgmode_timestamp(u"<1980-12-31 Wed 23:59>", +2),
            u"<1981-01-01 Thu 01:59>" )

        self.assertEqual(
            OrgFormat.apply_timedelta_to_Orgmode_timestamp(u"<1981-01-01 Thu 01:59>", -2),
            u"<1980-12-31 Wed 23:59>" )

        self.assertEqual(
            OrgFormat.apply_timedelta_to_Orgmode_timestamp(u"<2009-12-07 Mon 12:25>-<2009-12-07 Mon 12:26>", -2),
            u"<2009-12-07 Mon 10:25>-<2009-12-07 Mon 10:26>" )


    def tearDown(self):
        pass

########NEW FILE########
__FILENAME__ = phonecalls_test
# -*- coding: utf-8 -*-
# Time-stamp: <2012-09-06 22:02:48 armin>

import unittest
import os
from memacs.phonecalls import PhonecallsMemacs


class TestPhonecallsMemacs(unittest.TestCase):

    def setUp(self):
        test_file = os.path.dirname(os.path.abspath(__file__)) + \
            os.sep + "tmp" + os.sep + "calls.xml"
        argv = "-s -f " + test_file
        memacs = PhonecallsMemacs(argv=argv.split())
        self.data = memacs.test_get_entries()

    def test_from_file(self):
        data = self.data

        # generate assertEquals :)
#        for d in range(len(data)):
#            print "self.assertEqual(\n\tdata[%d],\n\t \"%s\")" % \
#               (d, data[d])

        self.assertEqual(
            data[0],
             "** <2011-08-05 Fri 17:05:06> Phonecall from +43691234123" + \
             " Duration: 59 sec")
        self.assertEqual(
            data[1],
             "   :PROPERTIES:")
        self.assertEqual(
            data[2],
            "   :ID:         5d4b551b7804f763ab2a62d287628aedee3e17a4")
        self.assertEqual(
            data[3],
             "   :END:")
        self.assertEqual(
            data[4],
             "** <2011-08-05 Fri 10:46:55> Phonecall to 06612341234 " + \
             "Duration: 22 sec")
        self.assertEqual(
            data[5],
             "   :PROPERTIES:")
        self.assertEqual(
            data[6],
            "   :ID:         8a377f25d80b1c137fcf6f28835d234141dfe179")
        self.assertEqual(
            data[7],
             "   :END:")
        self.assertEqual(
            data[8],
             "** <2011-08-05 Fri 07:51:31> Phonecall from Unknown Number " + \
             "Duration: 382 sec")
        self.assertEqual(
            data[9],
             "   :PROPERTIES:")
        self.assertEqual(
            data[10],
            "   :ID:         556373e703194e9919489f3497b485b63b9e6978")
        self.assertEqual(
            data[11],
             "   :END:")
        self.assertEqual(
            data[12],
             "** <2011-08-04 Thu 18:25:27> Phonecall from +4312341234 " + \
             "Duration: 289 sec")
        self.assertEqual(
            data[13],
             "   :PROPERTIES:")
        self.assertEqual(
            data[14],
            "   :ID:         6cc7b095acf4b4ac7d647821541ad4b3c611d56e")
        self.assertEqual(
            data[15],
             "   :END:")
        self.assertEqual(
            data[16],
             "** <2011-08-04 Thu 16:45:34> Phonecall from +4366412341234" + \
             " Duration: 70 sec")
        self.assertEqual(
            data[17],
             "   :PROPERTIES:")
        self.assertEqual(
            data[18],
            "   :ID:         8865ef73de0bb1dc9d9de0b362f885defda9ada1")
        self.assertEqual(
            data[19],
             "   :END:")
        self.assertEqual(
            data[20],
             "** <2011-08-04 Thu 16:02:31> Phonecall to +4366234123" + \
             " Duration: 0 sec")
        self.assertEqual(
            data[21],
             "   :PROPERTIES:")
        self.assertEqual(
            data[22],
            "   :ID:         8561807f509b66f3a8dd639b19776a2a06e0463e")
        self.assertEqual(
            data[23],
             "   :END:")
        self.assertEqual(
            data[24],
             "** <2011-08-04 Thu 15:21:40> Phonecall missed +436612341234" + \
             " Duration: 0 sec")
        self.assertEqual(
            data[25],
             "   :PROPERTIES:")
        self.assertEqual(
            data[26],
            "   :ID:         1f1ebb7853e28d66d6908f72a454cec378011605")
        self.assertEqual(
            data[27],
             "   :END:")
        self.assertEqual(
            data[28],
             "** <2011-08-04 Thu 14:36:02> Phonecall to +433123412" + \
             " Duration: 60 sec")
        self.assertEqual(
            data[29],
             "   :PROPERTIES:")
        self.assertEqual(
            data[30],
            "   :ID:         9558d013e3522e5bcbb02cb6599182ca0802547d")
        self.assertEqual(
            data[31],
             "   :END:")

########NEW FILE########
__FILENAME__ = photos_test
# -*- coding: utf-8 -*-
# Time-stamp: <2014-05-03 17:46:44 vk>

import unittest
import os
from memacs.photos import PhotosMemacs


class TestPhotoMemacs(unittest.TestCase):

    def test_from_file(self):
        test_path = os.path.dirname(os.path.abspath(__file__)) + \
            os.sep + "tmp"
        argv = "-s -f " + test_path
        memacs = PhotosMemacs(argv=argv.split())
        data = memacs.test_get_entries()

        # generate assertEquals :)
#        for d in range(len(data)):
#            print "self.assertEqual(\n\tdata[%d],\n\t \"%s\")" % \
#               (d, data[d])

        self.assertEqual(
            data[0],
             u"** <2000-08-04 Fri 18:22> [[/home/vk/src/memacs/mema" + \
             "cs/tests/tmp/fujifilm-finepix40i.jpg][fujifilm-finepix40i.jpg]]")
        self.assertEqual(
            data[1],
             "   :PROPERTIES:")
        self.assertEqual(
            data[2],
             u"   :ID:         c2833ac1c683dea5b600ac4f303a572d2148e1e7")
        self.assertEqual(
            data[3],
             "   :END:")

########NEW FILE########
__FILENAME__ = rss_test
# -*- coding: utf-8 -*-
# Time-stamp: <2011-10-28 15:13:31 aw>

import unittest
import os
from memacs.rss import RssMemacs


class TestRss(unittest.TestCase):

    def setUp(self):
        self.test_file = os.path.dirname(
            os.path.abspath(__file__)) + os.sep + "tmp" \
            + os.path.sep + "sample-rss.txt"
        self.argv = "-s -f " + self.test_file

    def test_false_appending(self):
        try:
            memacs = RssMemacs(argv=self.argv.split())
            memacs.test_get_entries()
        except Exception:
            pass

    def test_all(self):
        memacs = RssMemacs(argv=self.argv.split())
        data = memacs.test_get_entries()

        # generate assertEquals :)
        #for d in range(len(data)):
        #    print "self.assertEqual(\n\tdata[%d],\n\t\"%s\")" % \
        #        (d, data[d])
        self.assertEqual(
            data[0],
            "** <2009-09-06 Sun 16:45> [[http://www.wikipedia.or" + \
            "g/][Example entry]]")
        self.assertEqual(
            data[1],
            "   Here is some text containing an interesting description.")
        self.assertEqual(
            data[2],
            "   :PROPERTIES:")
        self.assertEqual(
            data[3],
            "   :GUID:       unique string per item")
        self.assertEqual(
            data[4],
            "   :ID:         7ec7b2ec7d1ac5f18188352551b04f061af81e04")
        self.assertEqual(
            data[5],
            "   :END:")

########NEW FILE########
__FILENAME__ = simplephonelogs_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-09-16 19:13:46 vk>

import unittest
import time
import datetime
import os
from memacs.simplephonelogs import SimplePhoneLogsMemacs
from memacs.lib.reader import CommonReader

## FIXXME: (Note) These test are *not* exhaustive unit tests. They only 
##         show the usage of the methods. Please add "mean" test cases and
##         borderline cases!


class TestSimplePhoneLogs_Basics(unittest.TestCase):

    argv = False
    logmodule = False
    input_file = False
    result_file = False
    maxDiff = None  ## show also large diff

    def setUp(self):

        self.result_file = os.path.dirname(
            os.path.abspath(__file__)) + os.path.sep + "phonelog-result-TEMP-DELETEME.org"

        self.input_file = os.path.dirname(
            os.path.abspath(__file__)) + os.path.sep + "phonelog-input-TEMP-DELETEME.csv"

        self.argv = "--suppress-messages --file " + self.input_file + " --output " + self.result_file



    def tearDown(self):

        os.remove(self.result_file)
        os.remove(self.input_file)


    def get_result_from_file(self):
        """reads out the resulting file and returns its content
        without header lines, main heading, last finish message, and
        empty lines"""

        result_from_module = CommonReader.get_data_from_file(self.result_file)

        result_from_module_without_header_and_last_line = u''

        ## remove header and last line (which includes execution-specific timing)
        for line in result_from_module.split('\n'):
            if line.startswith(u'* successfully parsed ') or \
                    line.startswith(u'#') or \
                    line.startswith(u'* ') or \
                    line == u'':
                pass
            else:
                result_from_module_without_header_and_last_line += line + '\n'

        return result_from_module_without_header_and_last_line


    def test_boot_without_shutdown(self):

        with open(self.input_file, 'w') as inputfile:
            inputfile.write('2013-04-05 # 13.39 # boot # 42 # 612\n')

        self.logmodule = SimplePhoneLogsMemacs(argv = self.argv.split())
        self.logmodule.handle_main()

        result = self.get_result_from_file()

        self.assertEqual(result, u"""** <2013-04-05 Fri 13:39> boot
   :PROPERTIES:
   :IN-BETWEEN:   
   :BATT-LEVEL:   42
   :UPTIME:       0:10:12
   :UPTIME-S:     612
   :IN-BETWEEN-S: 
   :ID:           50f3642555b86335789cc0850ee02652765b30a8
   :END:
""")


    def test_shutdown_with_boot(self):

        with open(self.input_file, 'w') as inputfile:
            inputfile.write('1970-01-01 # 00.01 # shutdown # 1 # 1\n' +
                            '2013-04-05 # 13.39 # boot # 42 # 612\n')

        self.logmodule = SimplePhoneLogsMemacs(argv = self.argv.split())
        self.logmodule.handle_main()

        result = self.get_result_from_file()

        self.assertEqual(result, u"""** <1970-01-01 Thu 00:01> shutdown
   :PROPERTIES:
   :IN-BETWEEN:   
   :BATT-LEVEL:   1
   :UPTIME:       0:00:01
   :UPTIME-S:     1
   :IN-BETWEEN-S: 
   :ID:           908b94cc00a0981c811f8392b85d4b5603476907
   :END:
** <2013-04-05 Fri 13:39> boot (off for 15800d 13:38:00)
   :PROPERTIES:
   :IN-BETWEEN:   379213:38:00
   :BATT-LEVEL:   42
   :UPTIME:       0:10:12
   :UPTIME-S:     612
   :IN-BETWEEN-S: 1365169080
   :ID:           0602b98ba31416e5ae7e2964455de121c7492a70
   :END:
""")
        

    def test_crashrecognition(self):


        with open(self.input_file, 'w') as inputfile:
            inputfile.write('2013-04-05 # 13.25 # shutdown # 1 # 10\n' +
                            '2013-04-05 # 13.30 # boot # 2 # 11\n' +
                            '2013-04-05 # 13.39 # boot # 3 # 12\n')

        self.logmodule = SimplePhoneLogsMemacs(argv = self.argv.split())
        self.logmodule.handle_main()

        result = self.get_result_from_file()

        self.assertEqual(result, u"""** <2013-04-05 Fri 13:25> shutdown
   :PROPERTIES:
   :IN-BETWEEN:   
   :BATT-LEVEL:   1
   :UPTIME:       0:00:10
   :UPTIME-S:     10
   :IN-BETWEEN-S: 
   :ID:           0ec0d92a33e4476756659fe6ca0ab78fc470747c
   :END:
** <2013-04-05 Fri 13:30> boot (off for 0:05:00)
   :PROPERTIES:
   :IN-BETWEEN:   0:05:00
   :BATT-LEVEL:   2
   :UPTIME:       0:00:11
   :UPTIME-S:     11
   :IN-BETWEEN-S: 300
   :ID:           5af2d989502a85deefc296936e9bf59087ecec2b
   :END:
** <2013-04-05 Fri 13:39> boot after crash
   :PROPERTIES:
   :IN-BETWEEN:   
   :BATT-LEVEL:   3
   :UPTIME:       0:00:12
   :UPTIME-S:     12
   :IN-BETWEEN-S: 
   :ID:           00903218ae1c5d02f79f9d527c5767dce580f10f
   :END:
""")







class TestSimplePhoneLogs_full_example_file(unittest.TestCase):

    logmodule = False

    def setUp(self):

        result_file = os.path.dirname(
            os.path.abspath(__file__)) + os.path.sep + "sample-phonelog-result-TEMP.org"

        self.test_file = os.path.dirname(
            os.path.abspath(__file__)) + os.sep + "tmp" \
            + os.path.sep + "sample-phonelog.csv"

        self.argv = "-s -f " + self.test_file + " --output " + result_file

        self.logmodule = SimplePhoneLogsMemacs(argv = self.argv.split())
        self.logmodule.handle_main()


    def test_determine_opposite_eventname(self):

        self.assertEqual(self.logmodule._determine_opposite_eventname(u"boot"), u'shutdown')
        self.assertEqual(self.logmodule._determine_opposite_eventname(u'shutdown'), u'boot')
        self.assertEqual(self.logmodule._determine_opposite_eventname(u'foo'), u'foo-end')
        self.assertEqual(self.logmodule._determine_opposite_eventname(u'foo-end'), u'foo')


    def test_parser(self):

        result_file = os.path.dirname(
            os.path.abspath(__file__)) + os.path.sep + "sample-phonelog-result-TEMP.org"

        argv = "-f " + self.test_file + \
            " --output " + result_file

        localmodule = SimplePhoneLogsMemacs(argv = argv.split())
        localmodule.handle_main()

        result_from_module = CommonReader.get_data_from_file(result_file)

        result_from_module_without_header_and_last_line = u''
        for line in result_from_module.split('\n'):
            if line.startswith(u'* successfully parsed ') or \
                    line.startswith(u'#') or \
                    line.startswith(u'* '):
                pass
            else:
                result_from_module_without_header_and_last_line += line + '\n'

        ## self.reference_result is defined below!
        self.assertEqual(result_from_module_without_header_and_last_line, self.reference_result)
        
        os.remove(result_file)



    maxDiff = None  ## show also large diff

    reference_result = u"""** <2012-11-20 Tue 11:56> boot
   :PROPERTIES:
   :IN-BETWEEN:   
   :BATT-LEVEL:   89
   :UPTIME:       1:51:32
   :UPTIME-S:     6692
   :IN-BETWEEN-S: 
   :ID:           746417eaaf657df53a744aa10bc925fef8b7901b
   :END:

** <2012-11-20 Tue 11:56> boot
   :PROPERTIES:
   :IN-BETWEEN:   
   :BATT-LEVEL:   89
   :UPTIME:       1:51:34
   :UPTIME-S:     6694
   :IN-BETWEEN-S: 
   :ID:           2da1bc746cdb4ca6f1a4d5c77673212d8a9ff762
   :END:

** <2012-11-20 Tue 19:59> shutdown (on for 8:03:00)
   :PROPERTIES:
   :IN-BETWEEN:   8:03:00
   :BATT-LEVEL:   72
   :UPTIME:       9:54:42
   :UPTIME-S:     35682
   :IN-BETWEEN-S: 28980
   :ID:           49ac414c512872a3d29465f41fd65a9e31f70ab2
   :END:

** <2012-11-20 Tue 21:32> boot (off for 1:33:00)
   :PROPERTIES:
   :IN-BETWEEN:   1:33:00
   :BATT-LEVEL:   71
   :UPTIME:       0:01:57
   :UPTIME-S:     117
   :IN-BETWEEN-S: 5580
   :ID:           3220003537db597474a361e023f2e610fd8437fc
   :END:

** <2012-11-20 Tue 23:52> shutdown (on for 2:20:00)
   :PROPERTIES:
   :IN-BETWEEN:   2:20:00
   :BATT-LEVEL:   63
   :UPTIME:       2:22:04
   :UPTIME-S:     8524
   :IN-BETWEEN-S: 8400
   :ID:           9b2addfa63569cddd56d8c725177948568368834
   :END:

** <2012-11-21 Wed 07:23> boot (off for 7:31:00)
   :PROPERTIES:
   :IN-BETWEEN:   7:31:00
   :BATT-LEVEL:   100
   :UPTIME:       0:01:55
   :UPTIME-S:     115
   :IN-BETWEEN-S: 27060
   :ID:           03547e5c9ea339b2a4350021a1c180161ba0324e
   :END:

** <2012-11-21 Wed 07:52> wifi-home
   :PROPERTIES:
   :IN-BETWEEN:   
   :BATT-LEVEL:   95
   :UPTIME:       0:31:19
   :UPTIME-S:     1879
   :IN-BETWEEN-S: 
   :ID:           9a65cf95dcf23a2a5add2238888cc7158e8615b6
   :END:

** <2012-11-21 Wed 08:17> wifi-home-end (home for 0:25:00)
   :PROPERTIES:
   :IN-BETWEEN:   0:25:00
   :BATT-LEVEL:   92
   :UPTIME:       0:56:18
   :UPTIME-S:     3378
   :IN-BETWEEN-S: 1500
   :ID:           d600d9aeddde8a0a8109c5b2def1091b46ecb2ab
   :END:

** <2012-11-21 Wed 13:06> boot after crash
   :PROPERTIES:
   :IN-BETWEEN:   
   :BATT-LEVEL:   77
   :UPTIME:       0:02:04
   :UPTIME-S:     124
   :IN-BETWEEN-S: 
   :ID:           70ccb21b1c0e75e93fcdc70d1eed5c24c5657074
   :END:

** <2012-11-21 Wed 21:08> wifi-home (not home for 12:51:00)
   :PROPERTIES:
   :IN-BETWEEN:   12:51:00
   :BATT-LEVEL:   50
   :UPTIME:       8:03:53
   :UPTIME-S:     29033
   :IN-BETWEEN-S: 46260
   :ID:           300798be8d2f9182995f823667122622e71298b4
   :END:

** <2012-11-22 Thu 00:12> shutdown (on for 16:49:00)
   :PROPERTIES:
   :IN-BETWEEN:   16:49:00
   :BATT-LEVEL:   39
   :UPTIME:       11:08:09
   :UPTIME-S:     40089
   :IN-BETWEEN-S: 60540
   :ID:           050e9723a23cd063e869ae7464a2a6a9e878055a
   :END:

** <2012-11-29 Thu 08:47> boot (off for 7d 8:35:00)
   :PROPERTIES:
   :IN-BETWEEN:   176:35:00
   :BATT-LEVEL:   100
   :UPTIME:       0:01:54
   :UPTIME-S:     114
   :IN-BETWEEN-S: 635700
   :ID:           b3ae1a136db220c283607a9e16c9828aa246f6be
   :END:

** <2012-11-29 Thu 08:48> wifi-home (not home for 8d 0:31:00)
   :PROPERTIES:
   :IN-BETWEEN:   192:31:00
   :BATT-LEVEL:   100
   :UPTIME:       0:01:58
   :UPTIME-S:     118
   :IN-BETWEEN-S: 693060
   :ID:           ab3e1a1af54520f76470ec6a26ca6879eafb67dc
   :END:

** <2012-11-29 Thu 09:41> wifi-home-end (home for 0:53:00)
   :PROPERTIES:
   :IN-BETWEEN:   0:53:00
   :BATT-LEVEL:   98
   :UPTIME:       0:55:17
   :UPTIME-S:     3317
   :IN-BETWEEN-S: 3180
   :ID:           0b105cc35f0df367357e25c5c87061e61c132321
   :END:

** <2012-11-29 Thu 14:46> wifi-office
   :PROPERTIES:
   :IN-BETWEEN:   
   :BATT-LEVEL:   81
   :UPTIME:       6:00:33
   :UPTIME-S:     21633
   :IN-BETWEEN-S: 
   :ID:           7e9e6f886f4b6445cb7bb2046dfe8bfc1fc787ff
   :END:

** <2012-11-29 Thu 16:15> wifi-home (not home for 6:34:00)
   :PROPERTIES:
   :IN-BETWEEN:   6:34:00
   :BATT-LEVEL:   76
   :UPTIME:       7:29:15
   :UPTIME-S:     26955
   :IN-BETWEEN-S: 23640
   :ID:           3118600d6f3c8e14cad6ae718b1e37303f19b95a
   :END:

** <2012-11-29 Thu 17:04> wifi-home-end (home for 0:49:00)
   :PROPERTIES:
   :IN-BETWEEN:   0:49:00
   :BATT-LEVEL:   74
   :UPTIME:       8:18:32
   :UPTIME-S:     29912
   :IN-BETWEEN-S: 2940
   :ID:           05a37ed12bb8968ea200b966d8d50568221d180d
   :END:

** <2012-11-29 Thu 23:31> shutdown (on for 14:44:00)
   :PROPERTIES:
   :IN-BETWEEN:   14:44:00
   :BATT-LEVEL:   48
   :UPTIME:       14:45:46
   :UPTIME-S:     53146
   :IN-BETWEEN-S: 53040
   :ID:           1388ccd5e0c9a54e166b41be1431eae18b6c5031
   :END:

** <2013-09-10 Tue 07:00> boot (off for 284d 7:29:00)
   :PROPERTIES:
   :IN-BETWEEN:   6823:29:00
   :BATT-LEVEL:   100
   :UPTIME:       0:02:10
   :UPTIME-S:     130
   :IN-BETWEEN-S: 24564540
   :ID:           1ab501758e7c68e6ce9455dc0262cc66947b52a5
   :END:

** <2013-09-10 Tue 08:23> wifi-office
   :PROPERTIES:
   :IN-BETWEEN:   
   :BATT-LEVEL:   95
   :UPTIME:       1:23:16
   :UPTIME-S:     4996
   :IN-BETWEEN-S: 
   :ID:           721bed72de6ba9295e7e0c5ca26414b1cbc819b5
   :END:

** <2013-09-10 Tue 12:13> wifi-office-end (office for 3:50:00; today 3:50:00; today total 3:50:00)
   :PROPERTIES:
   :IN-BETWEEN:   3:50:00
   :BATT-LEVEL:   87
   :UPTIME:       5:13:46
   :UPTIME-S:     18826
   :IN-BETWEEN-S: 13800
   :ID:           c668c3a34c5b6e8260c8b512af4697079d48cdc0
   :END:

** <2013-09-10 Tue 12:59> wifi-office (not office for 0:46:00)
   :PROPERTIES:
   :IN-BETWEEN:   0:46:00
   :BATT-LEVEL:   85
   :UPTIME:       6:00:00
   :UPTIME-S:     21600
   :IN-BETWEEN-S: 2760
   :ID:           4b681ff00c7ce3a8475319c10488b5d623dfb451
   :END:

** <2013-09-10 Tue 17:46> wifi-office-end (office for 4:47:00; today 8:37:00; today total 9:23:00)
   :PROPERTIES:
   :IN-BETWEEN:   4:47:00
   :BATT-LEVEL:   73
   :UPTIME:       10:47:06
   :UPTIME-S:     38826
   :IN-BETWEEN-S: 17220
   :ID:           754e6caaa22dc067440d4e0336dc3fd9b58faf22
   :END:

** <2013-09-10 Tue 22:10> shutdown (on for 15:10:00)
   :PROPERTIES:
   :IN-BETWEEN:   15:10:00
   :BATT-LEVEL:   58
   :UPTIME:       15:10:38
   :UPTIME-S:     54638
   :IN-BETWEEN-S: 54600
   :ID:           e1fe490c7090ba02640e9f01bb6f29d7973fbb1d
   :END:

** <2013-09-11 Wed 12:15> boot (off for 14:05:00)
   :PROPERTIES:
   :IN-BETWEEN:   14:05:00
   :BATT-LEVEL:   87
   :UPTIME:       5:15:05
   :UPTIME-S:     18905
   :IN-BETWEEN-S: 50700
   :ID:           c135298c813b09d23150777f7fa82cd6070db427
   :END:

** <2013-09-11 Wed 13:19> wifi-office (not office for 19:33:00)
   :PROPERTIES:
   :IN-BETWEEN:   19:33:00
   :BATT-LEVEL:   82
   :UPTIME:       6:19:29
   :UPTIME-S:     22769
   :IN-BETWEEN-S: 70380
   :ID:           35b64d133eb69ff2527769b3f836a352a9918bea
   :END:

** <2013-09-11 Wed 18:55> wifi-office-end (office for 5:36:00; today 5:36:00; today total 5:36:00)
   :PROPERTIES:
   :IN-BETWEEN:   5:36:00
   :BATT-LEVEL:   69
   :UPTIME:       11:56:01
   :UPTIME-S:     42961
   :IN-BETWEEN-S: 20160
   :ID:           d67377260ad01ee8794224392c858b171ddfbf11
   :END:

** <2013-09-11 Wed 19:10> wifi-home (not home for 286d 2:06:00)
   :PROPERTIES:
   :IN-BETWEEN:   6866:06:00
   :BATT-LEVEL:   68
   :UPTIME:       12:10:46
   :UPTIME-S:     43846
   :IN-BETWEEN-S: 24717960
   :ID:           d3a6e6cc276d43ce021f391c2a7443f4cf2957b9
   :END:

** <2013-09-11 Wed 22:55> shutdown (on for 10:40:00)
   :PROPERTIES:
   :IN-BETWEEN:   10:40:00
   :BATT-LEVEL:   53
   :UPTIME:       15:55:23
   :UPTIME-S:     57323
   :IN-BETWEEN-S: 38400
   :ID:           740eab692eb65559a005511d8926546bd780d787
   :END:


"""


# Local Variables:
# mode: flyspell
# eval: (ispell-change-dictionary "en_US")
# End:

########NEW FILE########
__FILENAME__ = sms_test
# -*- coding: utf-8 -*-
# Time-stamp: <2012-03-09 15:36:52 armin>

import unittest
import os
from memacs.sms import SmsMemacs


class TestSmsMemacs(unittest.TestCase):

    def setUp(self):
        test_file = os.path.dirname(os.path.abspath(__file__)) + \
            os.sep + "tmp" + os.sep + "smsxml.txt"
        argv = "-s -f " + test_file
        memacs = SmsMemacs(argv=argv.split())
        self.data = memacs.test_get_entries()

    def test_from_file(self):
        data = self.data

        # generate assertEquals :)
#        for d in range(len(data)):
#            print "self.assertEqual(\n\tdata[%d],\n\t \"%s\")" % \
#               (d, data[d])

        self.assertEqual(
            data[0],
             "** <2011-08-04 Thu 10:05:53> SMS from +436812314" + \
             "123: did you see the new sms memacs module?")
        self.assertEqual(
            data[1],
             "   :PROPERTIES:")
        self.assertEqual(
            data[2],
            "   :ID:         9a7774b7a546119af169625366350ca6cf1675f8")
        self.assertEqual(
            data[3],
             "   :END:")
        self.assertEqual(
            data[4],
             "** <2011-08-04 Thu 16:04:55> SMS to +43612341234: Memacs FTW!")
        self.assertEqual(
            data[5],
             "   :PROPERTIES:")
        self.assertEqual(
            data[6],
            "   :ID:         2163c59e66a84c391a1a00014801a2cb760b0125")
        self.assertEqual(
            data[7],
             "   :END:")
        self.assertEqual(
            data[8],
             "** <2011-08-04 Thu 20:25:50> SMS to +43612341238: i like memacs")
        self.assertEqual(
            data[9],
             "   :PROPERTIES:")
        self.assertEqual(
            data[10],
            "   :ID:         409d27ce4e9d08cce0acdea49b63b6d26b0b77c3")
        self.assertEqual(
            data[11],
             "   :END:")
        self.assertEqual(
            data[12],
             "** <2011-08-05 Fri 18:32:01> SMS to +4312341" + \
             "234: http://google.at")
        self.assertEqual(
            data[13],
             "   :PROPERTIES:")
        self.assertEqual(
            data[14],
            "   :ID:         4986730775a023fa0f268127f6ead9b8180337f0")
        self.assertEqual(
            data[15],
             "   :END:")

########NEW FILE########
__FILENAME__ = svn_test
# -*- coding: utf-8 -*-
# Time-stamp: <2011-10-28 15:13:31 aw>

import unittest
import os
from memacs.svn import SvnMemacs


class TestGitMemacs(unittest.TestCase):

    def setUp(self):
        test_file = os.path.dirname(os.path.abspath(__file__)) + \
            os.sep + "tmp" + os.sep + "svn-log-xml.txt"
        argv = "-s -f " + test_file
        memacs = SvnMemacs(argv=argv.split())
        self.data = memacs.test_get_entries()

    def test_from_file(self):
        data = self.data

        # generate assertEquals :)
        #for d in range(len(data)):
        #    print "self.assertEqual(\n\tdata[%d],\n\t \"%s\")" % \
        #       (d, data[d])

        self.assertEqual(
            data[0],
             "** <2011-10-27 Thu 17:50:16> group-5 (r5): finished ?")
        self.assertEqual(
            data[1],
             "   :PROPERTIES:")
        self.assertEqual(
            data[2],
             "   :REVISION:   5")
        self.assertEqual(
            data[3],
             "   :ID:         819908c0cedb0098bf5dd96aa0d213598da45614")
        self.assertEqual(
            data[4],
             "   :END:")
        self.assertEqual(
            data[5],
             "** <2011-10-27 Thu 17:18:26> group-5 (r4): finished 5,")
        self.assertEqual(
            data[6],
             "   added package to assignment1.tex for landscaping (see 5.tex)")
        self.assertEqual(
            data[7],
             "   :PROPERTIES:")
        self.assertEqual(
            data[8],
             "   :REVISION:   4")
        self.assertEqual(
            data[9],
             "   :ID:         629716ff44b206745fdc34c910fe8b0f3d877f85")
        self.assertEqual(
            data[10],
             "   :END:")
        self.assertEqual(
            data[11],
             "** <2011-10-27 Thu 15:38:17> group-5 (r3): 5b.")
        self.assertEqual(
            data[12],
             "   :PROPERTIES:")
        self.assertEqual(
            data[13],
             "   :REVISION:   3")
        self.assertEqual(
            data[14],
             "   :ID:         cf204bc9b36ba085275e03b7316ac34a496daf78")
        self.assertEqual(
            data[15],
             "   :END:")
        self.assertEqual(
            data[16],
             "** <2011-10-27 Thu 14:41:11> group-5 (r2): 5.tex")
        self.assertEqual(
            data[17],
             "   :PROPERTIES:")
        self.assertEqual(
            data[18],
             "   :REVISION:   2")
        self.assertEqual(
            data[19],
             "   :ID:         f45be418de175ccf56e960a6941c9973094ab9e3")
        self.assertEqual(
            data[20],
             "   :END:")
        self.assertEqual(
            data[21],
             "** <2011-10-27 Thu 08:44:55> group-5 (r1): initial files")
        self.assertEqual(
            data[22],
             "   :PROPERTIES:")
        self.assertEqual(
            data[23],
             "   :REVISION:   1")
        self.assertEqual(
            data[24],
             "   :ID:         9b7d570e2dc4fb3a009461714358c35cbe24a8fd")
        self.assertEqual(
            data[25],
             "   :END:")

########NEW FILE########
__FILENAME__ = twitter
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-09-14 14:49:06 vk>

import logging
import time
from datetime import datetime
from dateutil import parser
import os
import sys
from twython import Twython, TwythonError
from lib.orgformat import OrgFormat
from lib.memacs import Memacs
from lib.reader import UnicodeCsvReader
from lib.orgproperty import OrgProperties

class Twitter(Memacs):
    def _main(self):
        APP_KEY = self._get_config_option("APP_KEY")

        APP_SECRET = self._get_config_option("APP_SECRET")

        OAUTH_TOKEN = self._get_config_option("OAUTH_TOKEN")

        OAUTH_TOKEN_SECRET = self._get_config_option("OAUTH_TOKEN_SECRET")

        screen_name = self._get_config_option("screen_name")

        count = self._get_config_option("count")

        twitter = Twython(
            APP_KEY,
            APP_SECRET,
            OAUTH_TOKEN,
            OAUTH_TOKEN_SECRET
            )
        try:
            home_timeline = twitter.get_home_timeline(screenname=screen_name, count=count)

        except TwythonError as e:
            logging.error(e)
            sys.exit(1)

        for tweet in home_timeline:
            # strptime doesn't support timezone info, so we are using dateutils.
            date_object = parser.parse(tweet['created_at'])

            timestamp = OrgFormat.datetime(date_object)
            try:
                # Data is already Unicode, so don't try to re-encode it.
                output = tweet['text']
            except:
               logging.error(sys.exc_info()[0])
               print "Error: ", sys.exc_info()[0]

            data_for_hashing = output + timestamp + output
            properties = OrgProperties(data_for_hashing=data_for_hashing)

            properties.add("name", tweet['user']['name'])
            properties.add("twitter_id", tweet['id'])
            properties.add("contributors", tweet['contributors'])
            properties.add("truncated", tweet['truncated'])
            properties.add("in_reply_to_status_id", tweet['in_reply_to_status_id'])
            properties.add("favorite_count", tweet['favorite_count'])
            properties.add("source", tweet['source'])
            properties.add("retweeted", tweet['retweeted'])
            properties.add("coordinates", tweet['coordinates'])
            properties.add("entities", tweet['entities'])

            self._writer.write_org_subitem(timestamp=timestamp,
                                          output = output,
                                          properties = properties)

########NEW FILE########
__FILENAME__ = memacs-easybank
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-06-13 21:52:51 vk>

import os
import sys
import re
import time
import logging
from optparse import OptionParser
import codecs ## for writing unicode file
import pdb

## TODO:
## * fix parts marked with «FIXXME»

PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2011-10-09"
INVOCATION_TIME = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

## better performance if ReEx is pre-compiled:

## search for: «DD.MM.(.*)UM HH.MM»
TIMESTAMP_REGEX = re.compile(".*(([012]\d)|(30|31))\.((0\d)|(10|11|12))\..*UM ([012345]\d)\.([012345]\d).*")
## group 1: DD
TIMESTAMP_REGEX_DAYINDEX = 1  ## 2 is not always found
## group 2: DD
## group 3:
## group 4: MM
TIMESTAMP_REGEX_MONTHINDEX = 4  ## 5 is not always found
## group 5: MM
## group 6:
## group 7: HH
TIMESTAMP_REGEX_HOURINDEX = 7
## group 8: MM
TIMESTAMP_REGEX_MINUTEINDEX = 8
## group 9: nil

## search for: «DD.MM.YYYY»
DATESTAMP_REGEX = re.compile("([012345]\d)\.([012345]\d)\.([12]\d\d\d)")
DATESTAMP_REGEX_DAYINDEX = 1
DATESTAMP_REGEX_MONTHINDEX = 2
DATESTAMP_REGEX_YEARINDEX = 3

## search for: <numbers> <numbers> <nonnumbers>
BANKCODE_NAME_REGEX = re.compile("(\d\d\d\d+) (\d\d\d\d+) (.*)")

USAGE = u"\n\
         " + sys.argv[0] + u"\n\
\n\
This script parses bank statements «Umsatzliste» of easybank.at and generates \n\
an Org-mode file whose entry lines show the transactions in Org-mode agenda.\n\
\n\
Usage:  " + sys.argv[0] + u" <options>\n\
\n\
Example:\n\
     " + sys.argv[0] + u" -f ~/bank/transactions.csv -o ~/org/bank.org_archive\n\
\n\
\n\
:copyright: (c) 2011 by Karl Voit <tools@Karl-Voit.at>\n\
:license: GPL v2 or any later version\n\
:bugreports: <tools@Karl-Voit.at>\n\
:version: "+PROG_VERSION_NUMBER+" from "+PROG_VERSION_DATE+"\n"

parser = OptionParser(usage=USAGE)

parser.add_option("-f", "--file", dest="csvfilename",
                  help="a file that holds the transactions in CSV format", metavar="FILE")

parser.add_option("-o", "--output", dest="outputfile",
                  help="Org-mode file that will be generated (see above)." +\
                       " If no output file is given, result gets printed to stdout", metavar="FILE")

parser.add_option("-w", "--overwrite", dest="overwrite", action="store_true",
                  help="overwrite given output file without checking its existance")

parser.add_option("--version", dest="version", action="store_true",
                  help="display version and exit")

parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                  help="enable verbose mode")

(options, args) = parser.parse_args()


def handle_logging():
    """Log handling and configuration"""

    if options.verbose:
        FORMAT = "%(levelname)-8s %(asctime)-15s %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    else:
        FORMAT = "%(message)s"
        logging.basicConfig(level=logging.INFO, format=FORMAT)



def extract_datestamp_from_eventday(daystring):
    """extracts day, month, year from string like «DD.MM.YYYY»"""

    components = DATESTAMP_REGEX.match(daystring)

    if not components:
        logging.error("ERROR: could not parse date field: [" + daystring + "]")
        sys.exit(5)

    return components.group(DATESTAMP_REGEX_DAYINDEX),\
        components.group(DATESTAMP_REGEX_MONTHINDEX), \
        components.group(DATESTAMP_REGEX_YEARINDEX)


def extract_timestamp_from_timestampcomponents(timestampparts):
    """extracts the components of a time stamp from the timestampcomponents"""

    #logging.debug("found " + str(len(timestampparts.groups())) + " part(s) of timestamp within longdescription")
    month = timestampparts.group(TIMESTAMP_REGEX_MONTHINDEX)
    day = timestampparts.group(TIMESTAMP_REGEX_DAYINDEX)
    hour = timestampparts.group(TIMESTAMP_REGEX_HOURINDEX)
    minute = timestampparts.group(TIMESTAMP_REGEX_MINUTEINDEX)
    logging.debug("extracted timestamp: MM:dd [%s.%s] hh:mm [%s:%s] " % ( month, day, hour, minute) )
    return month, day, hour, minute


def generate_orgmodetimestamp(day, month, year, hour, minute):
    """generates <YYYY-MM-DD> or <YYYY-MM-DD HH:MM> from strings in arguments"""
    if hour and minute:
        timestring = " " + hour + ":" + minute
    else:
        timestring = ""
    return "<" + year + "-" + month + "-" + day + timestring + ">"


def extract_known_datasets(name, shortdescription, longdescription, descriptionparts):
    """handle known entries in the CSV file"""

    ## Auszahlung Maestro                           MC/000002270|BANKOMAT 29511 KARTE1 18.04.UM 11.34
    if descriptionparts[0].startswith(u'Auszahlung Maestro  '):
        logging.debug("found special case \"Auszahlung Maestro\"")
        name = None
        if len(descriptionparts)>1:
            shortdescription = descriptionparts[1].split(" ")[:2]  ## the 1st two words of the 2nd part
            shortdescription = " ".join(shortdescription)
        else:
            logging.warning("could not find descriptionparts[1]; using " + \
                                "\"Auszahlung Maestro\" instead")
            shortdescription = u"Auszahlung Maestro"
        logging.debug("shortdescr.=" + str(shortdescription))
            

    ## Bezahlung Maestro      MC/000002281|2108  K1 01.05.UM 17.43|OEBB 2483 FSA\\Ebreich sdorf         2483
    ## Bezahlung Maestro      MC/000002277|2108  K1 27.04.UM 17.10|OEBB 8020 FSA\\Graz                  8020
    ## Bezahlung Maestro      MC/000002276|WIENER LINIE 3001  K1 28.04.UM 19.05|WIENER LINIEN 3001     \
    ## Bezahlung Maestro      MC/000002272|BRAUN        0001  K1 19.04.UM 23.21|BRAUN DE PRAUN         \
    ## Bezahlung Maestro      MC/000002308|BILLA DANKT  6558  K1 11.06.UM 10.21|BILLA 6558             \
    ## Bezahlung Maestro      MC/000002337|AH10  K1 12.07.UM 11.46|Ecotec Computer Dat\\T imelkam       4850
    elif descriptionparts[0].startswith(u'Bezahlung Maestro  ') and len(descriptionparts)>2:
        logging.debug("found special case \"Bezahlung Maestro\"")
        shortdescription = descriptionparts[2].strip()  ## the last part
        name = None
        ## does not really work well with Unicode ... (yet)
        ##if shortdescription.startswith(u"OEBB"):
        ##    logging.debug("found special case \"ÖBB Fahrscheinautomat\"")
        ##    #shortdescription.replace("\\",' ')
        ##    logging.debug("sd[2]: [" + descriptionparts[2].strip() + "]")
        ##    re.sub(ur'OEBB (\d\d\d\d) FSA\\(.*)\s\s+(\\\d)?(\d\d+).*', ur'ÖBB Fahrschein \4 \2', descriptionparts[2].strip())

    elif descriptionparts[0].startswith(u'easykreditkarte MasterCard '):
        logging.debug("found special case \"easykreditkarte\"")
        name = None
        shortdescription = "MasterCard Abrechnung"

    elif len(descriptionparts)>1 and descriptionparts[0].startswith(u'Gutschrift Überweisung ') and \
            descriptionparts[1].startswith(u'TECHNISCHE UNIVERSITAET GRAZ '):
        logging.debug("found special case \"Gutschrift Überweisung, TUG\"")
        name = "TU Graz"
        shortdescription = "Gehalt"

    elif len(descriptionparts)>1 and descriptionparts[1] == u'Vergütung für Kontoführung':
        logging.debug("found special case \"Vergütung für Kontoführung\"")
        name = "easybank"
        shortdescription = u"Vergütung für Kontoführung"

    elif len(descriptionparts)>1 and descriptionparts[1] == u'Entgelt für Kontoführung':
        logging.debug("found special case \"Entgelt für Kontoführung\"")
        name = "easybank"
        shortdescription = u"Entgelt für Kontoführung"

    if name:
        logging.debug("changed name to: " + name)
    if shortdescription:
        logging.debug("changed shortdescription to: " + shortdescription)
    return name, shortdescription


def extract_name_and_shortdescription(longdescription):
    """
    Heuristic extraction of any information useful as name or short description.
    This is highly dependent on your personal account habit/data!
    """

    name = shortdescription = None

    ## shortdescription is first part of longdescriptions before the first two spaces
    shortdescription = longdescription[:longdescription.find("  ")]

    if len(shortdescription) < len(longdescription) and len(shortdescription) > 0:
        logging.debug("     extracted short description: [" + shortdescription + "]")
    else:
        shortdescription = None

    descriptionparts = longdescription.split('|')
    if len(descriptionparts) > 1:
        logging.debug("     found " + str(len(descriptionparts)) + " part(s) within longdescription, looking for name ...")
        bankcode_name = BANKCODE_NAME_REGEX.match(descriptionparts[1])
        if bankcode_name:
            name = bankcode_name.group(3)
            logging.debug("     found bank code and name. name is: [" + name + "]")

    ## so far the general stuff; now for parsing some known lines optionally overwriting things:
    name, shortdescription = extract_known_datasets(name, shortdescription, longdescription, descriptionparts)

    return name, shortdescription


def generate_orgmodeentry(orgmodetimestamp, jumptarget, amount, currency, longdescription, shortdescription, name):
    """generates the string for the Org-mode file"""

    ## ** $timestamp $amount $currency, [[bank:$jumptarget][$description]]
    ## if shortdescription:
    ## ** $timestamp $amount $currency, [[bank:$jumptarget][$shortdescription]]
    ## if name:
    ## ** $timestamp $amount $currency, [[contact:$name][name]], [[bank:$jumptarget][$description]]
    ## if name and shortdescription:
    ## ** $timestamp $amount $currency, [[contact:$name][name]], [[bank:$jumptarget][$(short)description]]

    if currency == u"EUR":
        currency = u"€"    # it's shorter :-)

    entry = u"** " + orgmodetimestamp + " " + amount + currency + ", "

    if name and len(name)>0:
        entry += u"[[contact:" + name + "][" + name + "]], "

    if shortdescription:
        entry += u"[[bank:" + jumptarget + "][" + shortdescription + "]]"
    else:
        entry += u"[[bank:" + jumptarget + "][" + longdescription + "]]"

    return entry


def parse_csvfile(filename, handler):
    """parses an csv file and generates orgmode entries"""

    basename = os.path.basename(filename).strip()
    logging.debug( "--------------------------------------------")
    logging.debug("processing file \""+ filename + "\" with basename \""+ basename + "\"")

    ## please do *not* use csvreader here since it is not able to handle UTF-8/latin-1!
    inputfile = codecs.open(filename, 'rb', 'latin-1')
    for line in inputfile:

        row = line.split(";")
        logging.debug("--------------------------------------------------------")
        logging.debug("processing row: " + unicode(str(row)) )

        ## direct data:
        try:
            longdescription = unicode(row[1])
            amount = unicode(row[4])
            currency = unicode(row[5]).strip()
            jumptarget = unicode(row[2]) + ";" + unicode(row[3]) + ";" + unicode(row[4])
        except UnicodeDecodeError as detail:
            logging.error("Encoding error: ")
            print detail
            logging.error("corresponding line is: [" + unicode(str(row)) + "]")
            sys.exit(4)

        ## derived data:
        timestampparts = TIMESTAMP_REGEX.match(longdescription)
        year = month = day = hour = minute = None
        orgmodetimestamp = None
        name = None   ## optional
        shortdescription = None   ## optional

        ## one line contains following values separated by «;»
        #logging.debug("account number: " + row[0] )
        logging.debug("long description: [" + longdescription + "]" )
        #logging.debug("day of clearing: " + row[2] )
        logging.debug("day of event: " + row[3] )
        logging.debug("amount: " + amount )
        #logging.debug("currency: " + currency )
        day, month, year = extract_datestamp_from_eventday(unicode(row[3]))
        if timestampparts:
            month, day, hour, minute = extract_timestamp_from_timestampcomponents(timestampparts)

        orgmodetimestamp = generate_orgmodetimestamp(day, month, year, hour, minute)

        name, shortdescription = extract_name_and_shortdescription(longdescription)

        orgmodeentry = generate_orgmodeentry(orgmodetimestamp, jumptarget, amount, \
                                             currency, longdescription, shortdescription, name)

        write_output(handler, orgmodeentry)


def write_output(handler, string):
    """write to stdout or to outfile"""

    if options.outputfile:
        handler.write(unicode(string) + u"\n")
    else:
        print string


def main():
    """Main function"""

    if options.version:
        print os.path.basename(sys.argv[0]) + " version "+PROG_VERSION_NUMBER+" from "+PROG_VERSION_DATE
        sys.exit(0)

    handle_logging()

    if not options.csvfilename:
        parser.error("Please provide an input file!")

    if not os.path.isfile(options.csvfilename):
    	print USAGE
    	logging.error("\n\nThe argument interpreted as an input file \"" + str(options.csvfilename) + \
                          "\" is not an normal file!\n")
        sys.exit(2)

    if not options.overwrite and options.outputfile and os.path.isfile(options.outputfile):
    	print USAGE
    	logging.error("\n\nThe argument interpreted as output file \"" + str(options.outputfile) + \
                          "\" already exists!\n")
        sys.exit(3)

    if options.outputfile:
        handler = codecs.open(options.outputfile, 'w', "utf-8")

    write_output(handler, u"## -*- coding: utf-8 -*-")
    write_output(handler, u"## this file is generated by " + sys.argv[0] + \
                     ". Any modifications will be overwritten upon next invocation!")
    write_output(handler, u"##    parameter input filename:  " + options.csvfilename)
    if options.outputfile:
        write_output(handler, u"##    parameter output filename: " + options.outputfile)
    else:
        write_output(handler, u"##    parameter output filename: none, writing to stdout")
    write_output(handler, u"##    invocation time:           " + INVOCATION_TIME)
    write_output(handler, u"* bank transactions                          :Memacs:bank:")

    parse_csvfile(options.csvfilename, handler)

    write_output(handler, u"* bank transcations above were successfully parsed by " + \
                     sys.argv[0] + " at " + INVOCATION_TIME + ".\n\n")

    if options.outputfile:
        handler.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        logging.info("Received KeyboardInterrupt")

## END OF FILE #################################################################

#end

########NEW FILE########
__FILENAME__ = memacs-mbox
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import time
import logging
from optparse import OptionParser

## TODO:
## - add command line argument to define link name to real content
##   currently: "file:INPUTFILE::ID" is used
##   desired:   "mylinkname:INPUTFILE::ID" should be used
##   additional: add explanation to readme (setq org-link-abbrev-alist)

PROG_VERSION_NUMBER = "0.1"
PROG_VERSION_DATE = "2011-09-16"
INVOCATION_TIME = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

## better performance if pre-compiled:
SUBJECT_REGEX = re.compile("Subject: (.*)")
FROM_REGEX = re.compile("From: (.*) <(.*)>")
NEWSGROUPS_REGEX = re.compile("Newsgroups: (.*)")
MESSAGEID_REGEX = re.compile("Message-I(d|D): (.*)")
HEADERSTART_REGEX = re.compile("From (.*) (Mon|Tue|Wed|Thu|Fri|Sat|Sun) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (([12]\d)|( 1| 2| 3| 4| 5| 5| 6| 7| 8| 9|30|31)) (([01]\d)|(20|21|22|23)):([012345]\d):([012345]\d) ([12]\d{3})")

## group 1: email: foo@gmx.at
## group 2: day: Fri
## group 3: month: May
## group 4: day: " 7"
## group 5: -
## group 6: day: " 7"
## group 7: hour: 13
## group 8: hour: 13
## group 9: -
## group 10: minutes: 54
## group 11: seconds: 15
## group 12: year: 2010

## From foo@gmx.at Fri May  7 13:54:15 2010
## From foo@bar-Voit.at Wed May 19 09:58:08 2010
## From foo@gmx.at Tue May 18 12:03:01 2010
## From foo@htu.tugraz.at Thu May  6 08:16:54 2010
## From foo@student.tugraz.at Fri May 21 16:01:09 2010
## From foo@bank.at Wed May  5 20:15:27 2010

## dd = " 1"..31: (([12]\d)|( 1| 2| 3| 4| 5| 5| 6| 7| 8| 9|30|31))
## hh = 01..24: (([01]\d)|(20|21|22|23))
## mm = 00..59: ([012345]\d)
## ss = 00..59: ([012345]\d)
## yyyy = 1000...2999: ([12]\d{3})

USAGE = "\n\
         "+sys.argv[0]+"\n\
\n\
This script parses mbox files (or newsgroup postings) and generates \n\
an Org-mode file whose entry lines show the emails in Org-mode agenda.\n\
\n\
Usage:  "+sys.argv[0]+" <options>\n\
\n\
Example:\n\
     ## simple example converting one mbox file:\n\
     "+sys.argv[0]+" -f ~/mails/business.mbox -o mails.org_archive\n\
\n\
     ## more advanced example with multiple files at once:\n\
     for myfile in ~/mails/*mbox\n\
        do "+sys.argv[0]+" -f \"${myfile}\" >> mails.org_archive\n\
     done\n\
\n\
\n\
:copyright: (c) 2011 by Karl Voit <tools@Karl-Voit.at>\n\
:license: GPL v2 or any later version\n\
:bugreports: <tools@Karl-Voit.at>\n\
:version: "+PROG_VERSION_NUMBER+" from "+PROG_VERSION_DATE+"\n"

parser = OptionParser(usage=USAGE)

parser.add_option("-f", "--file", dest="mboxname",
                  help="a file that holds the emails in mbox format", metavar="FILE")

parser.add_option("-o", "--output", dest="outputfile",
                  help="Org-mode file that will be generated (see above)." +\
                       " If no output file is given, result gets printed to stdout", metavar="FILE")

parser.add_option("-w", "--overwrite", dest="overwrite", action="store_true",
                  help="overwrite given output file without checking its existance")

parser.add_option("-n", "--newsgroup", dest="newsgroup", action="store_true",
                  help="mbox file contains newsgroup postings: ignore \"From:\", add \"Newsgroups:\"")

parser.add_option("--version", dest="version", action="store_true",
                  help="display version and exit")

parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                  help="enable verbose mode")

(options, args) = parser.parse_args()


def handle_logging():
    """Log handling and configuration"""

    if options.verbose:
        FORMAT = "%(levelname)-8s %(asctime)-15s %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    else:
        FORMAT = "%(message)s"
        logging.basicConfig(level=logging.INFO, format=FORMAT)


def get_timestamp_from_components(components):
    """returns orgmode timestamp of regex components"""

    ## resetting contact dictionary
    monthsdict = {'Jan':'01', 'Feb':'02', 'Mar':'03', 'Apr':'04', 'May':'05', \
           'Jun':'06', 'Jul':'07', 'Aug':'08', 'Sep':'09', 'Oct':'10', 'Nov':'11', 'Dec':'12' }

    ## group 1: email: foo@gmx.at
    ## group 2: day: Fri
    daystrid = 2
    ## group 3: month: May
    monthid = 3
    ## group 4: day: " 7"
    dayid = 4
    ## group 5: -
    ## group 6: day: " 7"
    ## group 7: hour: 13
    hourid = 7
    ## group 8: hour: 13
    ## group 9: -
    ## group 10: minutes: 54
    minuteid = 10
    ## group 11: seconds: 15
    ## group 12: year: 2010
    yearid = 12

    try:
        string =  "<" + components.group(yearid) + "-" + monthsdict[ components.group(monthid) ] + \
           "-" + components.group(dayid).strip().zfill(2) + " " + components.group(daystrid) + \
           " " + components.group(hourid) + ":" + components.group(minuteid) + ">"
    except IndexError, e:
        logging.error("Sorry, there were some problems parsing the timestamp of the current from line.")
        string = "ERROR"

    return string

def generate_output_line(timestamp, fromline, emailaddress, filename, messageid, subject):
    """generates an orgmode entry for an email"""

    if fromline == "":
        fromline = emailaddress

    string = "** " + timestamp
    if options.newsgroup:
        string += " " + fromline + ": "
    else:
        string += " [[contact:" + fromline + "][" + fromline + "]]: "

    string += "[[file:" + filename + "::" + messageid + "][" + subject + "]]"

    return string


def parse_mbox(filename, outputfile):
    """parses an mbox and generates orgmode entries"""

    basename = os.path.basename(filename).strip()
    logging.debug( "--------------------------------------------")
    logging.debug("processing line \""+ filename + "\" with basename \""+ basename + "\"")

    was_empty_line = True
    is_header = False
    last_firstline = "" ## holds the "From .*" line which is the first line of a new email/posting
    last_from = ""  ## holds real name for emails OR newsgroup name(s) for postings
    last_email = ""
    last_subject = ""
    last_message_id = ""
    last_orgmodetimestamp = ""

    for line in open(filename, 'r'):
        line=line.strip()

        if was_empty_line:
            ##logging.debug("was_empty_line is True")
            fromlinecomponents = HEADERSTART_REGEX.match(line)

        if is_header:
            logging.debug("parsing header line: " + line)
            ##logging.debug("is_header is True")
            subjectcomponents = SUBJECT_REGEX.match(line)
            if options.newsgroup:
                fromcomponents = NEWSGROUPS_REGEX.match(line)
            else:
                fromcomponents = FROM_REGEX.match(line)
            messageidcomponents = MESSAGEID_REGEX.match(line)

        if not is_header and was_empty_line and fromlinecomponents:
            logging.debug("new header: " + line)
            ## here the beginning of a new email header is assumed when an empty line
            ## is followed by a line that matches HEADERSTART_REGEX
            is_header = True
            last_email = fromlinecomponents.group(1)
            last_firstline = line
            last_from = ""
            last_subject = ""
            last_message_id = ""
            subjectcomponents = None
            messageidcomponents = None
            last_orgmodetimestamp = get_timestamp_from_components(fromlinecomponents)
            logging.debug("new email: " + last_email + " ... at " + last_orgmodetimestamp)

        elif is_header and subjectcomponents:
            last_subject = subjectcomponents.group(1).replace('[', '|').replace("]", "|")
            logging.debug("subject: " + last_subject)

        elif is_header and fromcomponents:
            last_from =  fromcomponents.group(1).replace('"', '').replace("'", "")
            logging.debug("from: " + last_from)

        elif is_header and messageidcomponents:
            last_message_id = messageidcomponents.group(2).replace('<', '').replace(">", "")
            if last_message_id == "":
                logging.error("Sorry, this entry had no correct message-id and is not jumpable in Orgmode.")
            logging.debug(last_message_id)

        if is_header and last_orgmodetimestamp != "" and last_subject != "" and last_message_id != "":
            logging.debug("entry written")
            if outputfile:
                outputfile.write( generate_output_line(last_orgmodetimestamp, last_from, last_email, \
                                                       filename, last_message_id, last_subject) )
                if options.newsgroup:
                    outputfile.write('\n')  ## FIXXME: Sorry for this but there seems to be different behaviour when doing newsgroups
            else:
                print generate_output_line(last_orgmodetimestamp, last_from, last_email, \
                                                       filename, last_message_id, last_subject).strip()
            is_header = False

        if line == "":
            was_empty_line = True
            if is_header and last_message_id == "":
                ## recover if only message-id was not found:
                ## (some NNTP-clients do not generate those and let the NNTP-server do it)
                last_message_id = last_firstline
                logging.warn("Current entry does not provide a Message-ID, using first From-line instead: " + last_firstline)
            elif is_header:
                logging.error("Current entry was not recognized as an entry. Missing value(s)?")
                if last_orgmodetimestamp:
                    logging.error("  timestamp:  " + last_orgmodetimestamp )
                else:
                    logging.error("  NO timestamp recognized!")
                logging.error("  subject:    " + last_subject )
                logging.error("  message-id: " + last_message_id )
                is_header = False
        else:
            was_empty_line = False


def main():
    """Main function"""

    if options.version:
        print os.path.basename(sys.argv[0]) + " version "+PROG_VERSION_NUMBER+" from "+PROG_VERSION_DATE
        sys.exit(0)

    handle_logging()

    if not options.mboxname:
        parser.error("Please provide an input file!")

    if not os.path.isfile(options.mboxname):
    	print USAGE
    	logging.error("\n\nThe argument interpreted as an input file \"" + str(options.mboxname) + \
                          "\" is not an normal file!\n")
        sys.exit(2)

    if not options.overwrite and options.outputfile and os.path.isfile(options.outputfile):
    	print USAGE
    	logging.error("\n\nThe argument interpreted as output file \"" + str(options.outputfile) + \
                          "\" already exists!\n")
        sys.exit(3)

    string = "## this file is generated by " + sys.argv[0] + \
                     ". Any modifications will be overwritten upon next invocation!\n"

    if options.newsgroup:
        string += "* Memacs module for newsgroup postings: " + options.mboxname + "                    :Memacs:news:"
    else:
        string += "* Memacs module for mbox emails: " + options.mboxname + "                         :Memacs:mbox:email:"

    if options.outputfile:
        output = open(options.outputfile, 'w')
        output.write(string + "\n")
    else:
        output = None
        print string

    parse_mbox(options.mboxname, output)

    string = "* this mbox is successfully parsed by " + sys.argv[0] + " at " + INVOCATION_TIME + "."

    if options.outputfile:
        output.write(string + "\n")
        output.close()
    else:
        print string


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Received KeyboardInterrupt")

## END OF FILE #################################################################

#end

########NEW FILE########
__FILENAME__ = memacs-filenametimestamps
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import time
import logging
from optparse import OptionParser

PROG_VERSION_NUMBER = "0.2"
PROG_VERSION_DATE = "2011-10-10"
INVOCATION_TIME = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
MATCHING_LEVEL = {'day': 1, 'minutes': 2, 'seconds': 3, 'notmatching': 4}

## better performance if pre-compiled:
TIMESTAMP_REGEX = re.compile("([12]\d{3})-([01]\d)-([0123]\d)T([012]\d).([012345]\d)(.([012345]\d))?")
DATESTAMP_REGEX = re.compile("([12]\d{3})-([01]\d)-([0123]\d)")

## RegEx matches more exactly:
##         reason: avoid 2011-01-00 (day is zero) or month is >12, ...
##         problem: mathing groups will change as well!
##   also fix in: vktimestamp2filedate
## dd = 01..31: ( ([12]\d) | (01|02|03|04|05|05|06|07|08|09|30|31) )
## mm = 01..12: ( ([0]\d) | (10|11|12) )
## hh = 00..23: ( ([01]\d) | (20|21|22|23) )

USAGE = "\n\
         "+sys.argv[0]+"\n\
\n\
This script parses a text file containing absolute paths to files\n\
with ISO datestamps and timestamps in their file names:\n\
\n\
Examples:  \"2010-03-29T20.12 Divegraph.tiff\"\n\
           \"2010-12-31T23.59_Cookie_recipies.pdf\"\n\
           \"2011-08-29T08.23.59_test.pdf\"\n\
\n\
Then an Org-mode file is generated that contains links to the files.\n\
\n\
Usage:  "+sys.argv[0]+" <options>\n\
\n\
Example:\n\
     ## generating a file containing all ISO timestamp filenames:\n\
     find $HOME -name '[12][0-9][0-9][0-9]-[01][0-9]-[0123][0-9]*' \ \n\
                                         -type f > $HOME/files.log\n\
     ## invoking this script:\n\
     "+sys.argv[0]+" -f $HOME/files.log -o result.org\n\
\n\
\n\
:copyright: (c) 2011 by Karl Voit <tools@Karl-Voit.at>\n\
:license: GPL v2 or any later version\n\
:bugreports: <tools@Karl-Voit.at>\n\
:version: "+PROG_VERSION_NUMBER+" from "+PROG_VERSION_DATE+"\n"

parser = OptionParser(usage=USAGE)

parser.add_option("-f", "--filelist", dest="filelistname",
                  help="file that holds the list of files (see above)", metavar="FILE")

parser.add_option("-o", "--output", dest="outputfile",
                  help="Org-mode file that will be generated (see above)", metavar="FILE")

parser.add_option("-w", "--overwrite", dest="overwrite", action="store_true",
                  help="overwrite given output file without checking its existance")

parser.add_option("--version", dest="version", action="store_true",
                  help="display version and exit")

parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                  help="enable verbose mode")

(options, args) = parser.parse_args()
# if we found a timestamp too, take hours,minutes and optionally seconds from this timestamp

def handle_logging():
    """Log handling and configuration"""

    if options.verbose:
        FORMAT = "%(levelname)-8s %(asctime)-15s %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    else:
        FORMAT = "%(message)s"
        logging.basicConfig(level=logging.INFO, format=FORMAT)


def get_timestamp_from_file(filename):
    """returns mtime of file"""
    return time.localtime( os.path.getmtime(filename) )



def check_if_days_in_timestamps_are_same(filename, basename, filenamedatestampcomponents):
    """handles timestamp differences for timestamps containing only day information (and not times)"""

    filetimestamp = get_timestamp_from_file(filename)[0:3]
    logging.debug( "filetimestamp " + str( filetimestamp ))

    filenamedatestampcomponentslist = map(lambda x: int(x), filenamedatestampcomponents.groups())  ## converts strings to integers
    filenamedatestampcomponentslist = list( filenamedatestampcomponentslist )  ## converts tuple to list

    logging.debug( "filenamedatestampcomponentslist " + str( filenamedatestampcomponentslist ))
        #logging.debug( "filenamedatestampcomponentslist[0] " + str( filenamedatestampcomponentslist[0] ))

    if filenamedatestampcomponentslist[0] == filetimestamp[0] and \
            filenamedatestampcomponentslist[1] == filetimestamp[1] and \
            filenamedatestampcomponentslist[2] == filetimestamp[2]:
        logging.debug("matches only date YYYY-MM-DD")
        return True
    else:
        logging.debug( "filetimestamp and filename differs: " + filename)
        return False




def generate_orgmode_file_timestamp(filename):
    """generates string for a file containing ISO timestamp in Org-mode"""

    ## Org-mode timestamp: <2011-07-16 Sat 9:00>
    ## also working in Org-mode agenda: <2011-07-16 9:00>

    basename = os.path.basename(filename)
    timestampcomponents = TIMESTAMP_REGEX.match(basename)
    ## "2010-06-12T13.08.42_test..." -> ('2010', '06', '12', '13', '08', '.42', '42')
    ## filenametimestampcomponents.group(1) -> '2010'

    datestampcomponents = DATESTAMP_REGEX.match(basename)

    if timestampcomponents:

        datestamp = "<" + str(timestampcomponents.group(1)) + "-" + str(timestampcomponents.group(2)) + "-" + str(timestampcomponents.group(3)) + \
            " " + str(timestampcomponents.group(4)) + ":" + str(timestampcomponents.group(5)) + ">"

        logging.debug("datestamp (time): " + datestamp)

        return "** " + datestamp + " [[file:" + filename + "][" + basename + "]]\n"

    elif datestampcomponents:

        if check_if_days_in_timestamps_are_same(filename, basename, datestampcomponents):
            logging.debug("day of timestamps is different, have to assume time")

            assumedtime = ""  ## no special time assumed; file gets shown as time-independent
            #assumedtime = " 12:00" ## files with no special time gets shown at noon

            datestamp = "<" + str(datestampcomponents.group(1)) + "-" + str(datestampcomponents.group(2)) + \
                "-" + str(datestampcomponents.group(3)) + assumedtime + ">"

            logging.debug("datestamp (day): " + datestamp)

            return "** " + datestamp + " [[file:" + filename + "][" + basename + "]]\n"

        else:
            logging.debug("day of timestamps is same, can use file time")

            filetimestampcomponents = get_timestamp_from_file(filename)
            timestamp = str(filetimestampcomponents[3]).zfill(2) + ":" + str(filetimestampcomponents[4]).zfill(2)

            datestamp = "<" + str(datestampcomponents.group(1)) + "-" + str(datestampcomponents.group(2)) + \
                "-" + str(datestampcomponents.group(3)) + " " + str(timestamp) + ">"

            logging.debug("datestamp (day): " + datestamp)

            return "** " + datestamp + " [[file:" + filename + "][" + basename + "]]\n"

    else:
        logging.warning("FIXXME: this point should never be reached. not recognizing datestamp or timestamp")
        return False




def handle_filelist_line(line, output):
    """handles one line of the list of files to check"""

    filename = line.strip()
    basename = os.path.basename(line).strip()
    logging.debug( "--------------------------------------------")
    logging.debug("processing line \""+ filename + "\" with basename \""+ basename + "\"")

    if filename == "":
        logging.debug( "ignoring empty line")

    elif not os.path.isfile(filename):
        logging.warn( "ignoring \""+ filename + "\" because it is no file")

    elif TIMESTAMP_REGEX.match(basename) or DATESTAMP_REGEX.match(basename):

        output.write( generate_orgmode_file_timestamp(filename) )

    else:
    	logging.warn( "ignoring \""+ filename + "\" because its file name does not match ISO date YYYY-MM-DDThh.mm(.ss)")



def main():
    """Main function"""

    if options.version:
        print os.path.basename(sys.argv[0]) + " version "+PROG_VERSION_NUMBER+" from "+PROG_VERSION_DATE
        sys.exit(0)

    handle_logging()

    if not options.filelistname:
        parser.error("Please provide an input file!")

    if not options.outputfile:
        parser.error("Please provide an output file!")

    if not os.path.isfile(options.filelistname):
    	print USAGE
    	logging.error("\n\nThe argument interpreted as an input file \"" + str(options.filelistname) + "\" is not an normal file!\n")
        sys.exit(2)

    if not options.overwrite and os.path.isfile(options.outputfile):
    	print USAGE
    	logging.error("\n\nThe argument interpreted as output file \"" + str(options.outputfile) + "\" already exists!\n")
        sys.exit(3)

    output = open(options.outputfile, 'w')

    output.write("## this file is generated by " + sys.argv[0] + ". Any modifications will be overwritten upon next invocation!\n")
    output.write("* Memacs file name datestamp                      :Memacs:filedatestamps:\n")

    for line in open(options.filelistname, 'r'):

        handle_filelist_line(line, output)

    output.write("* this file is successfully generated by " + sys.argv[0] + " at " + INVOCATION_TIME + ".\n")
    output.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Received KeyboardInterrupt")

## END OF FILE #################################################################

#end

########NEW FILE########
