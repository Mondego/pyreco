__FILENAME__ = alarm
#!/usr/bin/env python

"""
Alarm script
============

Author:  Laszlo Szathmary, 2011 (jabba.laci@gmail.com)
Website: https://ubuntuincident.wordpress.com/2011/04/17/alarm-script/
GitHub:  https://github.com/jabbalaci/Bash-Utils

A simple alarm script that plays a list of MP3s at a given time.
Very useful if you leave your computer switched on during the night.

Usage:
------

./alarm.py -p
    Play music. First do this to adjust volume! If the volume is low,
    you won't hear it in the morning.

./alarm.py -t 7h15
    Set alarm time. The format is HhM, where H is the hour (24-hour system),
    M is the minute, 'h' is the separator.

./alarm.py
    Set alarm with the default time. In my case it's 6h55.
"""

import os
import sys

from optparse import OptionParser
from datetime import datetime
from time import sleep
from random import shuffle


MUSIC_DIR = '/media/jabba/JIVE/mp3/sfa_scifi'
TRAVERSE_RECURSIVELY = True
MPLAYER = '/usr/bin/mplayer'
MPLAYER_OPTIONS = '-endpos 00:00:60'    # play first 60 seconds; disabled when -p is used
DEFAULT_TIME = '6h55'


class CollectMp3:
    """Collect music files recursively in a given directory."""
    def __init__(self, music_dir):
        self.music_dir = music_dir
        self.songs = []

    def traverse(self, directory):
        """Traverse directory recursively. Symlinks are skipped."""
        content = [os.path.join(directory, x) for x in os.listdir(directory)]
        dirs = sorted([x for x in content if os.path.isdir(x)])
        files = sorted([x for x in content if os.path.isfile(x)])

        for f in files:
            if os.path.islink(f):
                continue
            ext = os.path.splitext(f)[1]
            if ext in ('.mp3', '.flac', '.ogg', '.flv'):
                self.songs.append(f)

        if TRAVERSE_RECURSIVELY:
            for d in dirs:
                if os.path.islink(d):
                    continue
                self.traverse(d)

    def collect(self):
        """Collect songs, shuffle order, and print a little statistics."""
        self.traverse(self.music_dir)
        if self.get_number_of_songs() == 0:
            print "Error: there are no songs available."
            sys.exit(-1)
        # else
        shuffle(self.songs)
        header = "number of songs: {0}".format(self.get_number_of_songs())
        sep = '#' * (len(header) + 2 + 2)
        print sep
        print '# ' + header + ' #'
        print sep
        print

    def get_number_of_songs(self):
        return len(self.songs)

    def get_songs(self):
        return self.songs


collector = CollectMp3(MUSIC_DIR)

#############################################################################


def play_music():
    songs = collector.get_songs()
    for f in songs:
        val = os.system("{mplayer} {options} \"{song}\"".format(mplayer=MPLAYER, options=MPLAYER_OPTIONS, song=f))
        if val == 2:    # interrupted with CTRL-C
            sys.exit(val)


def set_alarm(hour, minute):
    # autoflush
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

    sep = "=" * 19
    print sep
    print "| Alarm at {0:2}h{1:02}. |".format(hour, minute)
    print sep

    alarm_time = hour * 100 + minute

    while True:
        now = datetime.now()
        time = datetime.time(now)
        current_time = time.hour * 100 + time.minute
        if (current_time >= alarm_time) and (current_time - alarm_time <= 100):
            play_music()
            sys.exit(0)
        else:
            sys.stdout.write('.')
            try:
                sleep(10)
            except KeyboardInterrupt:
                print
                break   # break out of 'while True'


def check_alarm(alarm_time):
    msg = "{0} error: there is a problem with the alarm time.".format(sys.argv[0])
    try:
        alarm_time = alarm_time.lower()
        if 'h' not in alarm_time:
            alarm_time += 'h'
        hour, minute = alarm_time.split('h')
        if not minute:
            minute = '0'
        hour = int(hour)
        minute = int(minute)
        if not ((0 <= hour <= 23) and (0 <= minute <= 59)):
            print >>sys.stderr, msg
            sys.exit(1)
    except ValueError:
        print >>sys.stderr, msg
        sys.exit(1)

    return hour, minute


def main(default=DEFAULT_TIME):
    parser = OptionParser(usage='%prog [options]')

    #[options]
    parser.add_option('-t',
                      '--time',
                      action='store',
                      default=default,
                      type='string',
                      dest='alarm_time',
                      help='Alarm time, ex.: 6h55.')

    parser.add_option('-p',
                      '--play',
                      action='store_true',
                      default=False,
                      dest='is_play',
                      help='Play music. Useful for adjusting the volume.')

    options, arguments = parser.parse_args()

    if options.is_play:
        global MPLAYER_OPTIONS
        MPLAYER_OPTIONS = ''
        print '# MPLAYER_OPTIONS is disabled'

    collector.collect()

    if options.is_play:
        play_music()    # play and
        sys.exit(0)     # quit
    # else
    if options.alarm_time:
        hour, minute = check_alarm(options.alarm_time)
        set_alarm(hour, minute)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = dictionary
#!/usr/bin/env python

"""
A very simple lookup of a word.
"""

import sys
import webbrowser


_template = 'http://www.thefreedictionary.com/p/{word}'


def process(word):
    url = _template.format(word=word)
    webbrowser.open(url)
    print '# see the result in your web browser'
    
    
#############################################################################


if __name__ == "__main__":
    if len(sys.argv) > 1:
        process(sys.argv[1])
    else:
        print >>sys.stderr, "{0}: error: specify a word.".format(sys.argv[0])
        sys.exit(1)

########NEW FILE########
__FILENAME__ = dropbox_permissions
#!/usr/bin/env python

"""
Setting file permissions in your Dropbox folder recursively
===========================================================

Author:  Laszlo Szathmary, 2011 (jabba.laci@gmail.com)
Website: https://ubuntuincident.wordpress.com/2011/05/08/setting-file-permissions-in-your-dropbox-folder-recursively/
GitHub:  https://github.com/jabbalaci/Bash-Utils (see the dropbox folder)

This script will change permissions only if permissions are not
correct. 
If we traverse our Dropbox folder recursively and set
permissions everywhere, Dropbox will synchronize ALL the files!
This script solves this problem by not modifying directories/files
whose permissions are good.

The Windows version of the Dropbox software regularly removes the 
executable flags. This script corrects that problem too.

Intended audience:
------------------
Linux users who also use Windows sometimes.

Usage:
------
Customize the header part, put the script in the root of your Dropbox
folder and launch it. Set DRY to False if you want to apply the
changes.
"""

import os
import sys
import stat

# dry run, make no changes just show them
DRY = True
#DRY = False

# verify if we are in the Dropbox folder
VERIFY_DROPBOX = True
#VERIFY_DROPBOX = False

# don't do anything with these folders:
ignore_dirs = ('.git', '.svn', '.eric4project', '.ropeproject')
# files with this extension will be executable:
executable_file_extensions = ('.py', '.sh', '.pl')
# these files will be executable:
executable_files_with_relative_path = (
    './xmind-portable/XMind_Linux/xmind',
    './xmind-portable/XMind_Linux/xmind-bin',
    './git.projects/others/upskirt/upskirt'
)

# some counters:
symlinks = 0
changes = 0


def chmod_ux(file):
    """Make a file executable.
    
    Apply chmod u+x on the file."""
    set_mode_to(file, 0700)


def set_mode_to(file, permissions):
    """Set the file with the given permissions."""
    global changes
    f = file
    mode = get_oct_mode(f)
    if mode != oct(permissions):
        try:
            if DRY:
                print "# chmod {0} {1}".format(oct(permissions), f)
            else:
                os.chmod(f, permissions)
            changes += 1
        except OSError:
            print >>sys.stderr, "# cannot chmod the file {0}".format(f)


def get_oct_mode(entry):
    """Get the permissions of an entry in octal mode.
    
    The return value is a string (ex. '0600')."""
    entry_stat = os.stat(entry)
    mode = oct(entry_stat[stat.ST_MODE] & 0777)
    return mode


def process_dir(directory):
    """Set the permissions of a directory."""
    set_mode_to(directory, 0700)


def process_file(file):
    """Set the permissions of a file."""
    f = file
    file_name = os.path.split(f)[1]
    file_ext = os.path.splitext(file_name)[1]

    if (file_ext in executable_file_extensions) or (f in executable_files_with_relative_path):
        process_exe_file(f)
    else:
        process_other_file(f)


def process_exe_file(file):
    """The file will be executable."""
    chmod_ux(file)


def process_other_file(file):
    """Normal file, not executable."""
    set_mode_to(file, 0600)


def skip_symlink(entry):
    """Symlinks are skipped.
    
    Imagine that you have a symlink that points out of your Dropbox folder to
    your HOME for instance. If we followed symlinks, the script would process
    your HOME directory too. We want the script to stay strictly in your
    Dropbox folder."""
    global symlinks
    symlinks += 1
    print "# skip symlink {0}".format(entry)


def traverse(directory):
    """Traverse directory recursively. Symlinks are skipped."""
    #content = [os.path.abspath(os.path.join(directory, x)) for x in os.listdir(directory)]
    content = [os.path.join(directory, x) for x in os.listdir(directory)]
    dirs = sorted([x for x in content if os.path.isdir(x)])
    files = sorted([x for x in content if os.path.isfile(x)])

    for d in dirs:
        if os.path.islink(d):
            skip_symlink(d)
            continue
        dir_name = os.path.split(d)[1]
        if dir_name in ignore_dirs:
            continue
        # else
        process_dir(d)
        traverse(d)
    
    for f in files:
        if os.path.islink(f):
            skip_symlink(f)
            continue
        # else
        process_file(f)


def verify_dir(directory):
    """ Verify if we are in the Dropbox folder."""
    d = os.path.abspath(directory)
    if 'dropbox' not in d.lower():
        print >>sys.stderr, """
It seems that you are not in the Dropbox folder. If you launch this
script in a wrong folder, it may do more harm than good since it
changes file permissions recursively.
If this is a false alarm and you really want to execute the script
here, disable this verification by setting the variable VERIFY_DROPBOX
to False.
"""
        sys.exit(1)


def main():
    """Controller."""
    start_dir = '.'
    if VERIFY_DROPBOX:
        verify_dir(start_dir)
    process_dir(start_dir)
    traverse(start_dir)
    #chmod_ux(sys.argv[0])
    print "# skipped symlinks: {0}".format(symlinks)
    print "# changes: {0}".format(changes)
    if DRY:
        print "# >>> it was a dry run, no changes were made <<<"

#############################################################################

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = get_public_link
#!/usr/bin/env python

"""
Get the public Dropbox links of several files
=============================================

Author:  Laszlo Szathmary, 2011 (jabba.laci@gmail.com)
Website: https://ubuntuincident.wordpress.com/2011/06/01/get-the-public-dropbox-links-of-several-files/
GitHub:  https://github.com/jabbalaci/Bash-Utils (see the dropbox/ folder)

The script shows the public Dropbox link(s) of one (or several) file(s).

Usage:
======

get_public_link <file>      # show the link of <file>

or

get_public_link -a          # show the links of all files in the current directory

If you want to copy the links to the clipboard, combine it with tocb.py:

get_public_link <file> | tocb
"""

import os
import sys

from optparse import OptionParser


# Your own Dropbox URL. No slash at the end.
BASE_URL = 'http://dl.dropbox.com/u/144888'
# Your own Dropbox folder in the local file system. No slash at the end.
BASE_PATH = '/home/jabba/Dropbox/Public'


def verify_file(abspath):
    """Verify if the entry exists and if it's a file (not a directory)."""
    if not os.path.isfile(abspath):
        print >>sys.stderr, "Error: I/O problem with {0}.".format(abspath)
        sys.exit(2)
    #
    verify_dir(os.path.split(abspath)[0])


def verify_dir(directory):
    """Verify if we are in the Dropbox/Public folder."""
    if BASE_PATH not in directory:
        print >>sys.stderr, "Error: you are not in the Dropbox/Public folder...."
        sys.exit(3)


def get_dropbox_link(abspath):
    """Get the public dropbox link of the file."""
    return abspath.replace(BASE_PATH, BASE_URL)


def process_file(file_name):
    """Process a single file."""
    f = os.path.abspath(file_name)
    verify_file(f)
    print get_dropbox_link(f)


def process_curr_dir():
    """Process all the files in the current directory."""
    cwd = os.getcwd()
    verify_dir(cwd)
    for file_name in sorted(os.listdir(cwd)):
        if os.path.isfile(file_name):
            f = os.path.abspath(file_name)
            print get_dropbox_link(f)


def check_constants():
    """Remove end slash if necessary."""
    global BASE_URL, BASE_PATH
    if BASE_URL.endswith('/'):
        BASE_URL = BASE_URL[:-1]
    if BASE_PATH.endswith('/'):
        BASE_PATH = BASE_PATH[:-1]


def main():
    """Controller."""

    check_constants()

    parser = OptionParser(usage='%prog <file> | -a')

    parser.add_option('-a',
                      '--all',
                      action='store_true',
                      default=False,
                      help='Get public links to all files in the current directory.')

    options, arguments = parser.parse_args()

    if len(arguments) == 0 and not options.all:
        parser.print_usage(),
        sys.exit(1)
    if len(arguments) > 0 and options.all:
        parser.print_usage(),
        sys.exit(1)

    # now either we have an argument xor we have the -a switch
    if len(arguments) > 0:
        process_file(arguments[0])

    if options.all:
        process_curr_dir()

#############################################################################

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = export_firefox_cookies
#!/usr/bin/env python

"""
Extract Firefox cookies
=======================

This script extracts cookies from Firefox's cookies.sqlite file
that are specific to a given host. The exported cookies are saved
in the file cookies.txt.

Then, you can use this exported file with wget to download content
that require authentication via cookies:

wget --cookies=on --load-cookies=cookies.txt --keep-session-cookies "http://..."

The original script was written by Dirk Sohler:
https://old.0x7be.de/2008/06/19/firefox-3-und-cookiestxt/

This version is a bit refactored but does exactly the same.
Website: https://ubuntuincident.wordpress.com/2011/09/05/download-pages-with-wget-that-are-protected-by-cookies/
GitHub:  https://github.com/jabbalaci/Bash-Utils (see the firefox/ folder)
"""

import os
import sys
import sqlite3 as db

USERDIR = 'w3z7c6j4.default'

COOKIEDB = os.path.expanduser('~') + '/.mozilla/firefox/' + USERDIR + '/cookies.sqlite'
OUTPUT = 'cookies.txt'
CONTENTS = "host, path, isSecure, expiry, name, value"


def extract(host):
    conn = db.connect(COOKIEDB)
    cursor = conn.cursor()

    sql = "SELECT {c} FROM moz_cookies WHERE host LIKE '%{h}%'".format(c=CONTENTS, h=host)
    cursor.execute(sql)

    out = open(OUTPUT, 'w')
    cnt = 0
    for row in cursor.fetchall():
        s = "{0}\tTRUE\t{1}\t{2}\t{3}\t{4}\t{5}\n".format(row[0], row[1],
                 str(bool(row[2])).upper(), row[3], str(row[4]), str(row[5]))
        out.write(s)
        cnt += 1

    print "Gesucht nach: {0}".format(host)
    print "Exportiert: {0}".format(cnt)

    out.close()
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print "{0}: error: specify the host.".format(sys.argv[0])
        sys.exit()
    else:
        extract(sys.argv[1])

########NEW FILE########
__FILENAME__ = get_alap
#!/usr/bin/env python

import os
import sys
import shutil

CWD = os.getcwd()
TEMPLATES = os.path.abspath(os.path.dirname(sys.argv[0])) + '/' + 'templates'
EXECUTABLE = ['py', 'd']
EDITOR = 'vim'


def rename(fname):
    dirName, fileName = os.path.split(fname)
    fileExt = os.path.splitext(fileName)[1]
    #
    reply = raw_input("New name of the file (without extension) [ENTER to cancel]: ").strip()
    if reply:
        to_name = dirName + '/' + reply + fileExt
        os.rename(fname, to_name)
        if os.path.isfile(to_name):
            print '# renamed to', os.path.split(to_name)[1]
            return to_name
        else:
            return None
    else:
        return fname


def copy(ext, full_name=None):
    if full_name:
        source = full_name
    else:
        source = 'alap.' + ext
    #
    if os.path.isfile(CWD + '/' + source):
        print >>sys.stderr, 'Warning: {} already exists in the current directory.'.format(source)
        sys.exit(1)
    # else
    dest = CWD + '/' + source
    shutil.copyfile(TEMPLATES + '/' + source, dest)
    if os.path.isfile(dest):
        print '# {} is created'.format(source)
        if ext in EXECUTABLE:
            os.chmod(dest, 0700)
    else:
        print "Warning: couldn't copy {}.".format(source)
        sys.exit(1)    # problem

    return rename(dest)


def edit(fname):
    ch = raw_input("Do you want to edit the file [y/n] (default: y)? ").strip()
    if ch=='y' or ch=='':
        os.system('{ed} "{f}"'.format(ed=EDITOR, f=fname))


def main():
    print """---------------------------
Create an empty source file
---------------------------
1) Python [py]
2) Go     [go]
3) Java   [java]
4) C      [c]
5) D      [d]
q) quit"""
    while True:
        try:
            ch = raw_input('> ')
        except (EOFError, KeyboardInterrupt):
            print
            ch = 'q'
        if ch in ['1', 'py']:
            return copy('py')
            break
        elif ch in ['2', 'go']:
            return copy('go')
            break
        elif ch in ['3', 'java']:
            return copy('java', full_name='Alap.java')
            break
        elif ch in ['4', 'c']:
            return copy('c')
            break
        elif ch in ['5', 'd']:
            return copy('d')
            break
        elif ch == 'q':
            print 'bye.'
            sys.exit(0)
        else:
            print 'Wat?'

#############################################################################

if __name__ == "__main__":
    fname = main()
    edit(fname)

########NEW FILE########
__FILENAME__ = get_images
#!/usr/bin/env python

"""
Extract image links from a web page
===================================
Author:  Laszlo Szathmary, 2011 (jabba.laci@gmail.com)
GitHub:  https://github.com/jabbalaci/Bash-Utils

Given a webpage, extract all image links.

Usage:
------
get_images.py URL [URL]... [options]

Options:
  -l, --length  Show lengths of images.
"""

import sys
import urllib
import urlparse

from optparse import OptionParser
from BeautifulSoup import BeautifulSoup


class MyOpener(urllib.FancyURLopener):
    version = 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15'
# MyOpener


def get_url_info(url):
    d = urllib.urlopen(url)
    return d.info()
# get_url_info


def process(url, options):
    myopener = MyOpener()
    #page = urllib.urlopen(url)
    page = myopener.open(url)

    text = page.read()
    page.close()

    soup = BeautifulSoup(text)

    for tag in soup.findAll('img', src=True):
        image_url = urlparse.urljoin(url, tag['src'])
        image_info = get_url_info(image_url)
        print image_url,
        if options.length:
            print image_info['Content-Length'],
        print
# process


def main():
    parser = OptionParser(usage='%prog URL [URL]... [options]')

    #[options]
    parser.add_option('-l',
                      '--length',
                      action='store_true',
                      default=False,
                      help='Show lengths of images.')

    options, arguments = parser.parse_args()

    if not arguments:
        parser.print_help()
        sys.exit(1)
    # else, if at least one parameter was passed
    for url in arguments:
        process(url, options)
# main

#############################################################################

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = get_links
#!/usr/bin/env python

"""
Extract all links from a web page
=================================
Author:  Laszlo Szathmary, 2011 (jabba.laci@gmail.com)
Website: https://pythonadventures.wordpress.com/2011/03/10/extract-all-links-from-a-web-page/
GitHub:  https://github.com/jabbalaci/Bash-Utils

Given a webpage, extract all links.

Usage:
------
./get_links.py <URL>
"""

import sys
import urllib
import urlparse

from BeautifulSoup import BeautifulSoup


class MyOpener(urllib.FancyURLopener):
    version = 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15'


def process(url):
    myopener = MyOpener()
    #page = urllib.urlopen(url)
    page = myopener.open(url)

    text = page.read()
    page.close()

    soup = BeautifulSoup(text)

    for tag in soup.findAll('a', href=True):
        tag['href'] = urlparse.urljoin(url, tag['href'])
        print tag['href']
# process(url)


def main():
    if len(sys.argv) == 1:
        print "Jabba's Link Extractor v0.1"
        print "Usage: %s URL [URL]..." % sys.argv[0]
        sys.exit(1)
    # else, if at least one parameter was passed
    for url in sys.argv[1:]:
        process(url)
# main()

#############################################################################

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = img_to_base64
#!/usr/bin/env python

"""
Image to BASE64
===============

Take an image file and encode it with BASE64. Put the encoded data in
an "img" HTML tag.

Author:  Laszlo Szathmary, 2011 (jabba.laci@gmail.com)
Website: https://ubuntuincident.wordpress.com/2011/04/17/embed-images-in-html-pages/
GitHub:  https://github.com/jabbalaci/Bash-Utils

Usage:
------

./img_to_base64.py <image_file>
    By default, the data is nested in an HTML tag and the output
    is wrapped. These settings can be customized.
    The output is printed to the standard output.

Sample output:
--------------

<img class='inline-image' src='data:image/gif;base64,R0lGODlhIgAbAPMPAGxsbNbW1v
/rhf/ge//3kf/Ub9/f3/b29oeHh/7LZv/0juazTktLS8WSLf//mf///yH5BAAAAAAALAAAAAAiABsAA
ASA8MlJq7046827/2AojiTVnI1xlFZjBisruU7tPCiqjg2h/L9KA2HgCQS5pE7UGLgwAhyCWWjYrrWE
owFgJqyEsDi82HZDja/jyGaXuV7rYE6fv8+gtLXA7/OtcCEGSoQMUyEHAQgAjI2OAAgBIwcGAZaXmAE
7Mpydnp+goaKjFBEAOw==' />
"""

import sys
import imghdr
import base64
import textwrap

# you can change the 'class' attribute or you can add more attributes
TEMPLATE = "<img class='inline-image'" + \
           " src='data:image/{0};base64,{1}' />"

# format options
HTML = 1        # one line, nested in TEMPLATE
BASE64 = 2      # one line, pure base64 encoded output
HTML_WRAP = 3   # wrapped HTML output, nested in TEMPLATE

# width fot text wrap
HTML_WRAP_WIDTH = 79


def convert_to_base64(filename, image_type, format=HTML):
    """Read the image file and encode it with base64.

    Return the image file either in an HTML img tag or as plain base64 text.
    """
    img = open(filename, 'rb')
    data = base64.b64encode(img.read())
    img.close()

    if format in [HTML, HTML_WRAP]:
        text = TEMPLATE.format(image_type, data)
        if format == HTML_WRAP:
            text = '\n'.join(textwrap.wrap(text, HTML_WRAP_WIDTH))
        return text
    # else
    if format == BASE64:
        return data
    # else
    return ''


def main(args):
    """Verify the format of the input file and print the base64 encoded text.

    Supported file formats: 'png' and 'jpeg'.
    """
    filename = args[0]
    image_type = imghdr.what(filename)

    if image_type not in ['png', 'jpeg', 'gif']:
        print "{0}: image file should be PNG, JPG or GIF.".format(sys.argv[0])
        sys.exit(1)
    # else
    print convert_to_base64(filename, image_type, format=HTML_WRAP)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print "{0}: missing image file argument.".format(sys.argv[0])
        sys.exit(0)
    else:
        main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = markdown
#!/usr/bin/env python

"""
Markdown previewer
==================
Author:  Laszlo Szathmary, 2011--2012 (jabba.laci@gmail.com)
Website: https://ubuntuincident.wordpress.com/2011/05/05/readme-markdown-on-github/
GitHub:  https://github.com/jabbalaci/Bash-Utils

Preview markdown files.

Usage:
------
Put it in your ~/bin directory (make sure ~/bin is in your PATH),
make it executable (chmod u+x ~/bin/markdown.py), and call it as
"markdown.py README.markdown". It will open the HTML output in a
new browser tab. Adding the "-u" switch (update), the HTML is not
opened in the browser.
"""

import os
import sys

MARKDOWN = 'markdown'   # /usr/bin/markdown (sudo apt-get install markdown)
SUNDOWN = 'sundown'     # https://github.com/tanoku/sundown

BROWSER = 'chromium-browser'

PROGRAM = MARKDOWN
VERBOSE = True


def main():
    update = False

    if len(sys.argv) < 2:
        print "Usage: {0} <file.markdown> [-u]".format(sys.argv[0])
        sys.exit(1)
    # else
    if '-u' in sys.argv:
        update = True
        sys.argv.remove('-u')
    input_file = sys.argv[1]
    os.system("{program} {input} > /tmp/markdown.html".format(program=PROGRAM, input=input_file))
    if not update:
        os.system("{browser} /tmp/markdown.html &".format(browser=BROWSER))
    if VERBOSE:
        print >>sys.stderr, "# renderer: {0}".format(PROGRAM)

#############################################################################

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = mousepos_gui
#!/usr/bin/env python

"""
Monitor the mouse position.

NEW
===

A new coordinate system can be defined in settings.json.
Then the script shows the absolute position (from the top left
corner), and the relative position too (from the new coordinate
system).
"""

import sys
import os

from time import sleep

import gtk
gtk.gdk.threads_init() #@UndefinedVariable

import threading

# uses the package python-xlib
# from http://snipplr.com/view/19188/mouseposition-on-linux-via-xlib/
# or: sudo apt-get install python-xlib
from Xlib import display

# By default, the position (0,0) is in the top left corner.
# However, you might want to re-position the coordinate
# system to somewhere else. X_0 and Y_0 marks the point (0,0)
# of this relative coordinate system.
import json
X_0 = 0  # to be read from settings.json
Y_0 = 0  # to be read from settings.json


def mousepos():
    """mousepos() --> (x, y) get the mouse coordinates on the screen (linux, Xlib)."""
    old_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    # this prints the string Xlib.protocol.request.QueryExtension to stdout,
    # that's why stdout is redirected temporarily to /dev/null
    data = display.Display().screen().root.query_pointer()._data
    sys.stdout = old_stdout

    return data["root_x"], data["root_y"]


class MouseThread(threading.Thread):
    def __init__(self, parent):
        threading.Thread.__init__(self)
        self.parent = parent
        self.killed = False

    def run(self):
        try:
            while True:
                if self.stopped():
                    break
                x, y = mousepos()
                text = "Abs: {0}".format((x, y))
                title = "A: {0}".format((x, y))
                if X_0 and Y_0:
                    text += " " * 15 + "Rel: {0}".format((x - X_0, y - Y_0))
                    title += " | R: {0}".format((x - X_0, y - Y_0))
                self.parent.label.set_text(text)
                self.parent.set_title(title)
                sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            sys.exit()

    def kill(self):
        self.killed = True

    def stopped(self):
        return self.killed


class PyApp(gtk.Window):

    def __init__(self):
        super(PyApp, self).__init__()

        #self.set_title("Mouse coordinates 0.1")
        self.set_keep_above(True)   # always on top
        self.set_size_request(300, 45)
        self.set_position(gtk.WIN_POS_CENTER)
        self.connect("destroy", self.quit)

        self.label = gtk.Label()

        self.mouseThread = MouseThread(self)
        self.mouseThread.start()

        fixed = gtk.Fixed()
        fixed.put(self.label, 10, 10)

        self.add(fixed)
        self.show_all()

    def quit(self, widget): #@ReservedAssignment
        self.mouseThread.kill()
        gtk.main_quit()


def read_settings():
    global X_0, Y_0
    #
    try:
        with open('settings.json') as f:
            settings = json.load(f)
        if 'x_0' in settings and 'y_0' in settings:
            X_0 = settings['x_0']
            Y_0 = settings['y_0']
    except IOError:
        print >>sys.stderr, 'Warning: settings.json is missing.'
    except ValueError:
        print >>sys.stderr, "Warning: couldn't decode settings.json"
    #
    print '# X_0:', X_0
    print '# Y_0:', Y_0

###################################################################################################

if __name__ == '__main__':
    read_settings()
    #
    app = PyApp()
    gtk.main()

########NEW FILE########
__FILENAME__ = open_in_tabs
#!/usr/bin/env python

"""
Open URLs in tabs
=================
Author:  Laszlo Szathmary, 2011 (jabba.laci@gmail.com)
Website: https://ubuntuincident.wordpress.com/2011/03/09/open-urls-in-browser-tabs-simultaneously/
GitHub:  https://github.com/jabbalaci/Bash-Utils

Read URLs from the standard input and open them in separated tabs.

Usage:
------
cat url_list.txt | ./open_in_tabs.py

Options:
  -n, --new-window      Open URLs in a new browser window.
  -s, --simultaneously  Open URLs simultaneously.

Warning! The combination -ns is experimental!
"""

import webbrowser
import sys
import commands
import shlex

from optparse import OptionParser
from subprocess import call
from time import sleep

__version__ = '0.3.0'

FIREFOX = webbrowser.get('firefox')
FIREFOX_PROCESS = 'firefox'         # look for it in the output of 'ps'
FIREFOX_EXE = 'firefox'                 # Firefox executable
DELAY = 3.0                             # seconds


def is_firefox_running():
    output = commands.getoutput('ps ux')
    return FIREFOX_PROCESS in output


def open_in_new_window(url, options, arguments):
    if options.simultaneously:
        command = "{0} -new-window {1}".format(FIREFOX_EXE, url)
        call(shlex.split(command))
        sleep(DELAY)
    else:
        FIREFOX.open_new(url)


def open_in_new_tab(url, options, arguments):
    if options.simultaneously:
        command = "{0} -new-tab {1}".format(FIREFOX_EXE, url)
        call(shlex.split(command))
    else:
        FIREFOX.open_new_tab(url)


def main():
    parser = OptionParser(usage='%prog [options]', version=__version__)

    #[options]
    parser.add_option('-n',
                      '--new-window',
                      action='store_true',
                      default=False,
                      help='Open URLs in a new browser window.')
    parser.add_option('-s',
                      '--simultaneously',
                      action='store_true',
                      default=False,
                      help='Open URLs simultaneously.')

    options, arguments = parser.parse_args()

    if options.new_window and options.simultaneously:
        print >>sys.stderr, \
            "# {0}: this combination is experimental.".format(sys.argv[0])
        #sys.exit(2)

    if not is_firefox_running():
        print >>sys.stderr, \
            "{0}: error: firefox is not running.".format(sys.argv[0])
        sys.exit(1)

    first = True
    for url in sys.stdin.readlines():
        url = url.rstrip("\n")

        if options.new_window:
            if first:
                open_in_new_window(url, options, arguments)
                first = False
            else:
                open_in_new_tab(url, options, arguments)
        else:
            open_in_new_tab(url, options, arguments)

    return 0

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = prettify
#!/usr/bin/env python

# Website: https://pythonadventures.wordpress.com/2011/04/03/prettify-html-with-beautifulsoup/
# Laszlo Szathmary, 2011 (jabba.laci@gmail.com)
#
# Prettify an HTML page. The script prints the HTML source
# that is built by BeautifulSoup (BS).
# Idea: if you want to manipulate a page with BS, analyze
#       the prettified source because this is how BS
#       stores it.
#
# Usage: prettify <URL>

import sys
import urllib
from BeautifulSoup import BeautifulSoup


class MyOpener(urllib.FancyURLopener):
    version = 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15'


def process(url):
    myopener = MyOpener()
    #page = urllib.urlopen(url)
    page = myopener.open(url)

    text = page.read()
    page.close()

    soup = BeautifulSoup(text)
    return soup.prettify()
# process(url)


def main():
    if len(sys.argv) == 1:
        print "Jabba's HTML Prettifier v0.1"
        print "Usage: %s <URL>" % sys.argv[0]
        sys.exit(-1)
    # else, if at least one parameter was passed
    print process(sys.argv[1])
# main()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = py2rtf
#!/usr/bin/env python

"""
py2rtf
======

Author:  Laszlo Szathmary, 2012 (jabba.laci@gmail.com)
Website: http://ubuntuincident.wordpress.com/2012/08/07/insert-syntax-highlighted-source-in-powerpoint/
GitHub:  https://github.com/jabbalaci/Bash-Utils

Transform a python source file to RTF.

What is it good for?
--------------------

You can open the RTF in Word, select it,
then paste into Powerpoint. This way you can have syntax
highlighted sources in your Powerpoint presentations.

Example:
--------

$ py2rtf hello.py       # the output is written to hello.rtf
$ py2rtf -f hello.py    # overwrite hello.rtf if exists
"""

import os
import sys


def process(args):
    """
    Check arguments, then call pygmentize with the
    appropriate parameters.
    """
    force = '-f' in args
    if force:
        args.remove('-f')
    if len(args) == 0:
        print >>sys.stderr, "Error: the input file is missing."
        sys.exit(1)
    # else
    in_file = args[0]
    (dirName, fileName) = os.path.split(in_file)
    (fileBaseName, fileExt) = os.path.splitext(fileName)
    out_file = os.path.join(dirName, fileBaseName + '.rtf')
    if not force and os.path.isfile(out_file):
        print >>sys.stderr, "Warning: the file {outf} exists.".format(outf=out_file)
        print >>sys.stderr, "Tip: use the -f option to force overwrite."
        sys.exit(1)
    # else
    cmd = 'pygmentize -f rtf -o {outf} {inf}'.format(outf=out_file, inf=in_file)
    print '#', cmd
    #
    os.system(cmd)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print >>sys.stderr, "Usage: {0} [-f] input.py".format(sys.argv[0])
    else:
        process(sys.argv[1:])

########NEW FILE########
__FILENAME__ = radio
#!/usr/bin/env python

"""
Play online radio stations
==========================
"""

import os
import sys


STATIONS = 'stations.csv'


def read_data():
    """Read the input .csv file."""
    li = []
    dic = {}
    with open(STATIONS, 'r') as f:
        for index, line in enumerate(f):
            li.append(line.rstrip("\n").split(';'))
            dic[li[-1][0]] = index

    return li, dic


def print_list(li):
    """Print station list to user."""
    print "Jabba's Minimalistic Radio Player :)"
    print
    for index, e in enumerate(li):
        pos = index + 1
        print "({pos}) {id:20}[{url}]".format(pos=pos, id=e[0], url=e[1])


def read_choice(li, dic):
    """Read user's choice and return the selected record."""
    print
    print "You can quit with 'q'."
    while True:
        record = None
        choice = raw_input("> ")
        if choice == '' or choice == 'q':
            sys.exit(0)
        # else
        try:
            # if it's a number
            if str(int(choice)) == choice:
                choice = int(choice)
        except ValueError:
            pass

        try:
            if isinstance(choice, int) and choice > 0:
                record = li[choice]
            elif isinstance(choice, str):
                record = li[dic[choice]]
        except IndexError:
            pass
        except KeyError:
            pass

        if record:
            break

    return record


def play_record(record):
    """Play station URL with mplayer."""
    station_url = record[1]
    cmd = "/usr/bin/mplayer '{url}'".format(url=station_url)
    os.system(cmd)


def main():
    """Controller."""
    li, dic = read_data()
    print_list(li[1:])
    record = read_choice(li, dic)
    play_record(record)

#############################################################################

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = reddit_get_all_pages
#!/usr/bin/env python

"""
Reddit, browse all pages of a subreddit
=======================================

Author:  Laszlo Szathmary, 2011 (jabba.laci@gmail.com)
Website: https://ubuntuincident.wordpress.com/2011/08/27/browse-all-pages-of-a-subreddit/
GitHub:  https://github.com/jabbalaci/Bash-Utils

When you visit a subreddit on reddit.com, for instance
http://www.reddit.com/r/python, at the bottom of the page
you will find just a "next" link to the next page.
Needless to say, browsing older entries like that is a PITA...
This script generates a simple static HTML page with links to
all the older pages: [1] [2] [3]...

Limitation
----------

This script made me figure out that reddit lists only the last 1000
posts! Older posts are hidden. If you have a direct link to them, fine,
otherwise they are gone :(
So this script will only list 40 pages. This is a limitation of reddit.

More info:

* http://www.reddit.com/r/help/comments/jhx5p/only_1000_posts_per_subreddit/
* http://www.reddit.com/r/help/comments/jhxmr/why_are_we_limited_in_the_number_of_links_we_can/

Usage:
------------

./reddit_get_all_pages.py
"""

import sys
import urllib
import json
import webbrowser

# no trailing slash:
BASE = 'http://www.reddit.com'
# This one can be customized. No trailing slash:
REDDIT = 'http://www.reddit.com/r/python'
#REDDIT = 'http://www.reddit.com/r/nsfw'
# output file:
OUTPUT_FILE = 'out.html'

page_cnt = 1


class HtmlWriter:
    def __init__(self):
        self.file = open(OUTPUT_FILE, 'w')
        self.add_header()
        print >>self.file, "<h2>{reddit}</h2>".format(reddit=REDDIT)

    def close(self):
        self.add_footer()
        self.file.close()
        print >>sys.stderr, "# the output was written to {out}".format(out=OUTPUT_FILE)

    def add(self, page, url):
        link = '<a href="{url}">{page}</a>'.format(url=url, page=page)
        print >>self.file, "[{link}] ".format(link=link)

    def add_header(self):
        print >>self.file, "<html>"
        print >>self.file, "<body>"

    def add_footer(self):
        print >>self.file, "</body>"
        print >>self.file, "</html>"


def add_json(reddit):
    reddit = reddit.replace('/?', '/.json?')
    if '/.json' not in reddit:
        reddit = reddit + '/.json'
    return reddit


def get_json_text(reddit):
    page = reddit
    sock = urllib.urlopen(page)
    json_text = sock.read()
    return json_text


def find_all_pages(reddit):
    global page_cnt

    html = HtmlWriter()

    while True:
        json_url = add_json(reddit)
        json_text = get_json_text(json_url)
        decoded = json.loads(json_text)
        posts = decoded['data']['children']
        if len(posts) == 0:
            break
        print >>sys.stderr, "# page {cnt:03}: {reddit}".format(cnt=page_cnt, reddit=reddit)
        html.add(page_cnt, reddit)
        last_post = posts[-1]
        name = last_post['data']['name']
        reddit = "{R}/?count=25&after={name}".format(R=REDDIT, name=name)
        page_cnt += 1

    html.close()


def main():
    find_all_pages(REDDIT)
    webbrowser.open(OUTPUT_FILE)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = reddit_get_posts
#!/usr/bin/env python

"""
Reddit, get posts
=================

Author:  Laszlo Szathmary, 2011 (jabba.laci@gmail.com)
Website: https://ubuntuincident.wordpress.com/2011/08/11/browse-your-favorite-subreddits-painlessly/
GitHub:  https://github.com/jabbalaci/Bash-Utils

This script can extract links to posts in a subreddit.
You can get links to comments (-c switch) or
to direct URLs (-u switch).

Basic usage:
------------

./reddit_get_posts.py -c /r/earthporn
    Get links to comments of subreddit "earthporn".

./reddit_get_posts.py -u /r/earthporn
    Get links to direct URLs of subreddit "earthporn".

./reddit_get_posts.py -u http://www.reddit.com/r/earthporn
    You can specify the complete URL of the subreddit.

./reddit_get_posts.py -u http://www.reddit.com/r/EarthPorn/?count=25&after=t3_jffyd
    You can even browse pages on reddit.com.

./reddit_get_posts.py -u
    Extract links of your favourite subreddit (specify it with the constant DEFAULT_REDDIT).


Advanced usage:
---------------

This script can be used together with another script of mine called open_in_tabs.py, which
is part of this Bash-Utils project too. open_in_tabs.py can open the extracted links in
your Firefox instance. Example:

./reddit_get_posts.py -u /r/earthporn | open_in_tabs -s
    This will open the links simultaneously (-s switch) in Firefox.
"""

import webbrowser
import urlparse
import urllib
import json
import sys

from optparse import OptionParser

# no trailing slash:
BASE = 'http://www.reddit.com'
# This one can be customized. No trailing slash:
DEFAULT_REDDIT = 'http://www.reddit.com/r/nsfw'

# don't hurt these constants:
REDDIT = DEFAULT_REDDIT
COMMENTS = 'permalink'
URL = 'url'
WHAT_TO_GET = ''


def init():
    global REDDIT
    REDDIT = REDDIT + '/.json'


def get_json_text():
    page = REDDIT
    print >>sys.stderr, "#", page
    sock = urllib.urlopen(page)
    json_text = sock.read()
    return json_text


def process_post(index, post):
    # indexing starts with 1 (instead of 0):
    index += 1
    url = urlparse.urljoin(BASE, post['data'][WHAT_TO_GET])
    print url
    webbrowser.open(url)


def process_posts(decoded):
    posts = decoded['data']['children']
    for i, post in enumerate(posts):
        process_post(i, post)


def verify_options(options):
    if not options.comments and not options.url:
        print >>sys.stderr, "{0}: you must specify what to extract.".format(sys.argv[0])
        sys.exit(1)

    if options.comments and options.url:
        print >>sys.stderr, "{0}: decide which one to extract.".format(sys.argv[0])
        sys.exit(1)


def verify_arguments(arguments):
    if len(arguments) > 1:
        print >>sys.stderr, \
            "{0}: you must specify one reddit in one of the following forms:\n\
/r/reddit or\n\
http://www.reddit.com/r/reddit".format(sys.argv[0])
        sys.exit(1)

    global REDDIT

    if len(arguments) == 1:
        arg = arguments[0]
        if arg.startswith('/r/'):
            REDDIT = "{base}{reddit}/.json".format(base=BASE, reddit=arg)
        elif arg.startswith('http'):
            REDDIT = arg
            REDDIT = REDDIT.replace('/?', '/.json?')
            if '/.json' not in REDDIT:
                REDDIT = REDDIT + '/.json'
        else:
            print >>sys.stderr, "{0}: argument error. It should look like /r/reddit or http://www.reddit.com/r/reddit .".format(sys.argv[0])
            sys.exit(1)


def main():
    init()
    parser = OptionParser(usage='%prog [options] [reddit]')

    #[options]
    parser.add_option('-c',
                      '--comments',
                      action='store_true',
                      default=False,
                      help='Get comment links.')
    parser.add_option('-u',
                      '--url',
                      action='store_true',
                      default=False,
                      help='Get URL links.')

    options, arguments = parser.parse_args()

    verify_options(options)
    verify_arguments(arguments)

    # else

    global WHAT_TO_GET
    if options.comments:
        WHAT_TO_GET = COMMENTS
    if options.url:
        WHAT_TO_GET = URL

    json_text = get_json_text()
    decoded = json.loads(json_text)
    process_posts(decoded)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = reddit_top10
#!/usr/bin/env python

"""
"""

import sys
import urllib
import json
import webbrowser
import operator
import time

# no trailing slash:
BASE = 'http://www.reddit.com'
# This one can be customized. No trailing slash:
REDDIT = 'http://www.reddit.com/r/python'
# output file:
OUTPUT_FILE = 'out.html'

BODY_BGCOLOR = '#EAF1FD'

LIMIT_PAGES = 1
LIMIT_TOP = None


class HtmlWriter:
    def __init__(self):
        self.old_stdout = sys.stdout
        self.f = open(OUTPUT_FILE, 'w')
        sys.stdout = self.f

        self.add_header()
        print "<h2>{reddit}</h2>".format(reddit=REDDIT)

    def process(self, posts):
        self.open_table()
        print """
<th>Index</th>
<th>#&nbsp;votes</th>
<th>#&nbsp;comments</th>
<th>Title</th>
<th>Date (yyyy.mm.dd.)</th>
"""
        global LIMIT_TOP
        if not LIMIT_TOP:
            LIMIT_TOP = len(posts.posts)

        for index, p in enumerate(posts.posts[:LIMIT_TOP]):
            pos = index + 1
            print '<tr>'
            print '<td><center>{pos}</center></td>'.format(pos=pos)
            print '<td><center><b>{score}</b></center></td>'.format(score=p.score)
            print '<td><center>{comments}</center></td>'.format(comments=p.comments_num)
            print '<td><a href="{url}">{title}</a></td>'.format(title=p.title, url=p.comments_url)
            print '<td>{date}</td>'.format(date=p.date_str())
            print '</tr>'
        self.close_table()
        self.close()

    def open_table(self):
        print '<table border="1" cellpadding="5">'

    def close_table(self):
        print '</table>'

    def close(self):
        self.add_footer()

        self.f.close()
        sys.stdout = self.old_stdout
        print >>sys.stderr, "# the output was written to {out}".format(out=OUTPUT_FILE)

    def add(self, page, url):
        link = '<a href="{url}">{page}</a>'.format(url=url, page=page)
        print "[{link}] ".format(link=link)

    def add_header(self):
        print """<html>
<head>
    <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
</head>
<body bgcolor="{c}">""".format(c=BODY_BGCOLOR)

    def add_footer(self):
        print "</body>"
        print "</html>"


class Posts:
    def __init__(self):
        self.posts = []

    def add(self, post):
        self.posts.append(post)

    def sort(self):
        self.posts.sort(key=operator.attrgetter("score"), reverse=True)

    def show(self):
        for post in self.posts[:LIMIT_TOP]:
            print post


class Post:
    def __init__(self, post):
        post = post['data']
        #self.score = post['score']     # minimum: 0
        self.score = post['ups'] - post['downs']    # this can go below 0 :)
        self.title = post['title'].encode('utf-8')
        self.comments_url = '{R}{url}'.format(R=BASE, url=post['permalink'].encode('utf-8'))
        self.secs = post['created']
        self.comments_num = post['num_comments']

    def __str__(self):
        sb = []
        sb.append('({score}) '.format(score=self.score))
        sb.append('[{title}]({url})'.format(title=self.title, url=self.comments_url))
        return ''.join(sb)

    def date_str(self):
        stime = time.gmtime(self.secs)
        return '{y}.{m:02d}.{d:02d}.'.format(y=stime[0], m=stime[1], d=stime[2])


def add_json(reddit):
    reddit = reddit.replace('/?', '/.json?')
    if '/.json' not in reddit:
        reddit = reddit + '/.json'
    return reddit


def get_json_text(reddit):
    page = reddit
    sock = urllib.urlopen(page)
    json_text = sock.read()
    return json_text


def traverse_pages(reddit, posts):
    page_cnt = 1

    while True:
        if LIMIT_PAGES and page_cnt > LIMIT_PAGES:
            break
        # else
        json_url = add_json(reddit)
        json_text = get_json_text(json_url)
        decoded = json.loads(json_text)
        children = decoded['data']['children']
        if len(children) == 0:
            break
        print >>sys.stderr, "# page {cnt:03}: {reddit}".format(cnt=page_cnt, reddit=reddit)
        for child in children:
            post = Post(child)
            posts.add(post)
        last_post = children[-1]
        name = last_post['data']['name']
        reddit = "{R}/?count=25&after={name}".format(R=REDDIT, name=name)
        page_cnt += 1

    return posts


def main():
    posts = Posts()
    html = HtmlWriter()

    posts = traverse_pages(REDDIT, posts)

    posts.sort()
    html.process(posts)
    #posts.show()
    webbrowser.open(OUTPUT_FILE)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = 01_submit
#!/usr/bin/env python

#Boa:Frame:Frame1

import wx
import reddit   # sudo pip install reddit

import config as cfg


def create(parent):
    return Frame1(parent)


[wxID_FRAME1, wxID_FRAME1BUTTON1, wxID_FRAME1BUTTON2, wxID_FRAME1BUTTON3,
 wxID_FRAME1BUTTON4, wxID_FRAME1PANEL1, wxID_FRAME1STATICLINE1,
 wxID_FRAME1STATICTEXT1, wxID_FRAME1STATICTEXT2, wxID_FRAME1STATICTEXT3,
 wxID_FRAME1TEXTCTRL1, wxID_FRAME1TEXTCTRL2, wxID_FRAME1TEXTCTRL3,
 wxID_FRAME1TEXTCTRL4, wxID_FRAME1BUTTON5, wxID_FRAME1BUTTON6,
] = [wx.NewId() for _init_ctrls in range(16)]


def get_clipboard_data():
    if not wx.TheClipboard.IsOpened():  # may crash, otherwise
        do = wx.TextDataObject()
        wx.TheClipboard.Open()
        success = wx.TheClipboard.GetData(do)
        wx.TheClipboard.Close()
        if success:
            return do.GetText()
        else:
            return ''


def submit_to_reddit(title, url, subreddit):
    r = reddit.Reddit(user_agent="submit to reddit script")
    r.login(user=cfg.USERNAME, password=cfg.PASSWORD)

    return r.submit(subreddit, url, title)


class Frame1(wx.Frame):
    def _init_ctrls(self, prnt):
        # generated method, don't edit
        wx.Frame.__init__(self, id=wxID_FRAME1, name='', parent=prnt,
              pos=wx.Point(597, 334), size=wx.Size(616, 601),
              style=wx.DEFAULT_FRAME_STYLE, title='submit to reddit')
        self.SetClientSize(wx.Size(616, 601))

        self.panel1 = wx.Panel(id=wxID_FRAME1PANEL1, name='panel1', parent=self,
              pos=wx.Point(0, 0), size=wx.Size(616, 601),
              style=wx.TAB_TRAVERSAL)

        self.staticText1 = wx.StaticText(id=wxID_FRAME1STATICTEXT1,
              label=u'title', name='staticText1', parent=self.panel1,
              pos=wx.Point(32, 24), size=wx.Size(47, 29), style=0)
        self.staticText1.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.NORMAL,
              False, u'Sans'))

        self.textCtrl1 = wx.TextCtrl(id=wxID_FRAME1TEXTCTRL1, name='textCtrl1',
              parent=self.panel1, pos=wx.Point(32, 64), size=wx.Size(424, 27),
              style=0, value='')

        self.button5 = wx.Button(id=wxID_FRAME1BUTTON5, label=u'paste',
              name='button5', parent=self.panel1, pos=wx.Point(495, 64),
              size=wx.Size(85, 29), style=0)
        self.button5.Bind(wx.EVT_BUTTON, self.OnButton5Button,
              id=wxID_FRAME1BUTTON5)

        self.button6 = wx.Button(id=wxID_FRAME1BUTTON6, label='clear',
              name='button6', parent=self.panel1, pos=wx.Point(495, 104),
              size=wx.Size(85, 29), style=0)
        self.button6.Bind(wx.EVT_BUTTON, self.OnButton6Button,
              id=wxID_FRAME1BUTTON6)

        self.staticText2 = wx.StaticText(id=wxID_FRAME1STATICTEXT2,
              label=u'url', name='staticText2', parent=self.panel1,
              pos=wx.Point(32, 130), size=wx.Size(32, 29), style=0)
        self.staticText2.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.NORMAL,
              False, u'Sans'))

        self.textCtrl2 = wx.TextCtrl(id=wxID_FRAME1TEXTCTRL2, name='textCtrl2',
              parent=self.panel1, pos=wx.Point(32, 170), size=wx.Size(424, 27),
              style=0, value='')

        self.staticText3 = wx.StaticText(id=wxID_FRAME1STATICTEXT3,
              label=u'choose a subreddit', name='staticText3',
              parent=self.panel1, pos=wx.Point(32, 250), size=wx.Size(230, 29),
              style=0)
        self.staticText3.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.NORMAL,
              False, u'Sans'))

        self.textCtrl3 = wx.TextCtrl(id=wxID_FRAME1TEXTCTRL3, name='textCtrl3',
              parent=self.panel1, pos=wx.Point(32, 290), size=wx.Size(424, 27),
              style=0, value=cfg.get_latest_subreddit())

        self.button1 = wx.Button(id=wxID_FRAME1BUTTON1, label=u'paste',
              name='button1', parent=self.panel1, pos=wx.Point(495, 170),
              size=wx.Size(85, 29), style=0)
        self.button1.Bind(wx.EVT_BUTTON, self.OnButton1Button,
              id=wxID_FRAME1BUTTON1)

        self.button2 = wx.Button(id=wxID_FRAME1BUTTON2, label='submit',
              name='button2', parent=self.panel1, pos=wx.Point(32, 360),
              size=wx.Size(85, 29), style=0)
        self.button2.Bind(wx.EVT_BUTTON, self.OnButton2Button,
              id=wxID_FRAME1BUTTON2)

        self.textCtrl4 = wx.TextCtrl(id=wxID_FRAME1TEXTCTRL4, name='textCtrl4',
              parent=self.panel1, pos=wx.Point(32, 440), size=wx.Size(544, 136),
              style=wx.TE_MULTILINE | wx.TE_READONLY, value='')
        self.textCtrl4.SetEditable(False)

        self.staticLine1 = wx.StaticLine(id=wxID_FRAME1STATICLINE1,
              name='staticLine1', parent=self.panel1, pos=wx.Point(32, 424),
              size=wx.Size(536, 2), style=0)

        self.button3 = wx.Button(id=wxID_FRAME1BUTTON3, label='clear',
              name='button3', parent=self.panel1, pos=wx.Point(495, 210),
              size=wx.Size(85, 29), style=0)
        self.button3.Bind(wx.EVT_BUTTON, self.OnButton3Button,
              id=wxID_FRAME1BUTTON3)

        self.button4 = wx.Button(id=wxID_FRAME1BUTTON4, label='reset',
              name='button4', parent=self.panel1, pos=wx.Point(130, 360),
              size=wx.Size(85, 29), style=0)
        self.button4.Bind(wx.EVT_BUTTON, self.OnButton4Button,
              id=wxID_FRAME1BUTTON4)

    def __init__(self, parent):
        self._init_ctrls(parent)

    def OnButton1Button(self, event):
        self.textCtrl2.SetValue(get_clipboard_data())
        event.Skip()

    def OnButton5Button(self, event):
        self.textCtrl1.SetValue(get_clipboard_data())
        event.Skip()

    def OnButton3Button(self, event):
        self.textCtrl2.SetValue('')
        event.Skip()

    def OnButton6Button(self, event):
        self.textCtrl1.SetValue('')
        event.Skip()

    def get_title(self):
        return self.textCtrl1.GetValue().strip()

    def get_url(self):
        return self.textCtrl2.GetValue().strip()

    def get_subreddit(self):
        return self.textCtrl3.GetValue().strip()

    def OnButton2Button(self, event):
        title = self.get_title()
        url = self.get_url()
        subreddit = self.get_subreddit()
        if not title or not url or not subreddit:
            self.textCtrl4.SetValue('Error: fill all fields.')
        else:
            self.textCtrl4.SetValue('submitting... (it can take some seconds)\n')
            result = submit_to_reddit(title, url, subreddit)
            self.textCtrl4.AppendText('\n')
            self.textCtrl4.AppendText(str(result) + '\n')
            cfg.set_latest_subreddit(subreddit)

        event.Skip()

    def OnButton4Button(self, event):
        self.textCtrl1.SetValue('')
        self.textCtrl2.SetValue('')
        self.textCtrl3.SetValue('')
        self.textCtrl4.SetValue('')
        event.Skip()


if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = create(None)
    frame.Show()

    app.MainLoop()

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python

import os

CREDENTIALS = '{home}/secret/reddit/credentials.txt'.format(home=os.path.expanduser('~'))
LATEST_SUBREDDIT = '{home}/secret/reddit/latest_subreddit.txt'.format(home=os.path.expanduser('~'))


def read_credentials():
    f = open(CREDENTIALS, 'r')
    user = f.readline().rstrip('\n')
    passwd = f.readline().rstrip('\n')
    f.close()

    return user, passwd

USERNAME, PASSWORD = read_credentials()


def get_latest_subreddit():
    try:
        f = open(LATEST_SUBREDDIT, 'r')
        text = f.readline().rstrip('\n')
        f.close()
    except IOError:
        return ''

    return text


def set_latest_subreddit(text):
    f = open(LATEST_SUBREDDIT, 'w')
    print >>f, text
    f.close()

#############################################################################

if __name__ == "__main__":
    print USERNAME, PASSWORD
    print get_latest_subreddit()

########NEW FILE########
__FILENAME__ = redirect_to
#!/usr/bin/env python

"""
Where does a URL redirect?
==========================

Author:  Laszlo Szathmary, 2011 (jabba.laci@gmail.com)
Website: http://pythonadventures.wordpress.com/2010/12/21/where-does-a-page-redirect-to/
GitHub:  https://github.com/jabbalaci/Bash-Utils

This script tells you where a webpage redirects.

Example:
--------

$ ./redirect_to.py http://bottlepy.org      # calling the script
http://bottlepy.org/docs/dev/               # output
"""

import sys
import urllib


def redirect(url):
    try:
        page = urllib.urlopen(url)
        return page.geturl()
    except:
        print 'Error: there is something wrong with that URL'
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print "Usage: {0} <url>".format(sys.argv[0])
    else:
        print redirect(sys.argv[1])

########NEW FILE########
__FILENAME__ = sp
#!/usr/bin/env python

# Website: https://ubuntuincident.wordpress.com/2011/03/17/show-the-absolute-path-of-a-file/
# Laszlo Szathmary, 2011 (jabba.laci@gmail.com)
#
# NEW! The path is also copied to the clipboard.
#
# Print the absolute path of a file.
# If no parameter is passed, show the current path.
# sp.py -> "show path"
#
# Usage: sp <filename>

import os
import sys
from tocb import text_to_clipboards


if len(sys.argv) == 1:
    text = os.getcwd()
else:
    text = os.path.join(os.getcwd(), sys.argv[1])

text = text.replace(' ', r'\ ')
print '# copied to the clipboard'
print text
text_to_clipboards(text)

########NEW FILE########
__FILENAME__ = alap
#!/usr/bin/env python


def main():
    # TODO...
    pass

##############################################################

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = tocb
#!/usr/bin/env python

# Website: https://pythonadventures.wordpress.com/2011/03/05/copy-string-to-x-clipboards/
# Laszlo Szathmary, 2011--2012 (jabba.laci@gmail.com)
#
# Copy the text from the standard input to ALL clipboards. Thus, you can use
# any paste method to insert your text (middle mouse button or Shift+Insert).
# tocb.py -> "to clipboard(s)"
#
# Requirement: xsel package (sudo apt-get install xsel).
#
# Usage: cat file.txt | tocb

import sys
import subprocess

#############################################################################


def text_to_clipboards(text):
    # "primary":
    xsel_proc = subprocess.Popen(['xsel', '-pi'], stdin=subprocess.PIPE)
    xsel_proc.communicate(text)
    # "clipboard":
    xsel_proc = subprocess.Popen(['xsel', '-bi'], stdin=subprocess.PIPE)
    xsel_proc.communicate(text)

#############################################################################

if __name__ == "__main__":
    stuff = sys.stdin.read()
    text_to_clipboards(stuff)

########NEW FILE########
__FILENAME__ = top10
#!/usr/bin/env python3
# encoding: utf-8

"""
Show the top 10 largest files in the current directory.
Bash command:

    find . -printf '%s %p\n'| sort -nr | head -10

Problem: it shows filesizes in bytes.

This script adds support to show filesizes
in a human-readable format.

Usage:

    # classical output in bytes
    ./top10.py

    # improved, human-readable output
    ./top10.py -h

Samples:

    /boot $ top10
    17458360 ./initrd.img-3.11.0-18-generic
    17456508 ./initrd.img-3.11.0-17-generic
    17451581 ./initrd.img-3.11.0-15-generic
    17303009 ./initrd.img-3.11.0-13-generic
    17302636 ./initrd.img-3.11.0-14-generic
    16397540 ./initrd.img-3.8.0-32-generic
    5634192 ./vmlinuz-3.11.0-18-generic
    5631792 ./vmlinuz-3.11.0-17-generic
    5631120 ./vmlinuz-3.11.0-15-generic
    5601072 ./vmlinuz-3.11.0-14-generic

    /boot $ top10 -h
    16.65M ./initrd.img-3.11.0-18-generic
    16.65M ./initrd.img-3.11.0-17-generic
    16.64M ./initrd.img-3.11.0-15-generic
    16.50M ./initrd.img-3.11.0-13-generic
    16.50M ./initrd.img-3.11.0-14-generic
    15.64M ./initrd.img-3.8.0-32-generic
    5.37M ./vmlinuz-3.11.0-18-generic
    5.37M ./vmlinuz-3.11.0-17-generic
    5.37M ./vmlinuz-3.11.0-15-generic
    5.34M ./vmlinuz-3.11.0-14-generic

Requires Python 3.
"""

import locale
import shlex
import subprocess as sp
import sys

encoding = locale.getdefaultlocale()[1]
HUMAN_READABLE = False


def sizeof_fmt(num):
    """
    Convert file size to human readable format.
    """
    for x in ['b', 'K', 'M', 'G', 'T']:
        if num < 1024.0:
            return "{0:.2f}{1}".format(num, x)
        num /= 1024.0


def human_readable(lines):
    for line in lines:
        num, fname = line.split(maxsplit=1)
        num = sizeof_fmt(int(num))
        print('{n} {f}'.format(n=num, f=fname))


def main():
    find = sp.Popen(shlex.split("find . -printf '%s %p\n'"), stdout=sp.PIPE)
    sort = sp.Popen(shlex.split("sort -nr"),
            stdin=find.stdout, stdout=sp.PIPE, stderr=sp.PIPE)
    out = sort.communicate()[0].decode(encoding).split("\n")
    out = out[:10]
    if HUMAN_READABLE:
        human_readable(out)
    else:
        for line in out:
            print(line)

##############################################################################

if __name__ == "__main__":
    if '-h' in sys.argv[1:]:
        HUMAN_READABLE = True
    #
    main()

########NEW FILE########
__FILENAME__ = us
#!/usr/bin/env python

# Change spaces to underscores.
# When to use: creating directories/files and we want to avoid spaces
#              in their names.
#
# Example:
# --------
# mv thinkpython.pdf `us "How to Think Like a Computer Scientist.pdf"`
#     => How_to_Think_Like_a_Computer_Scientist.pdf
#
# Usage: us <text>

import sys


def main(argv):
    if len(argv) > 1:
        text = argv[1]
        print text.replace(' ', '_')

if __name__ == "__main__":
    main(sys.argv)

########NEW FILE########
