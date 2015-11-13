__FILENAME__ = sheet
from cheat import sheets 
from cheat import utils
from cheat.utils import *
import os
import shutil
import subprocess


def copy(current_sheet_path, new_sheet_path):
    """ Copies a sheet to a new path """

    # attempt to copy the sheet to DEFAULT_CHEAT_DIR
    try:
        shutil.copy(current_sheet_path, new_sheet_path)

    # fail gracefully if the cheatsheet cannot be copied. This can happen if
    # DEFAULT_CHEAT_DIR does not exist
    except IOError:
        die ('Could not copy cheatsheet for editing.')


def create_or_edit(sheet):
    """ Creates or edits a cheatsheet """

    # if the cheatsheet does not exist
    if not exists(sheet):
        create(sheet)
    
    # if the cheatsheet exists and is writeable...
    elif exists(sheet) and is_writable(sheet):
        edit(sheet)

    # if the cheatsheet exists but is not writable...
    elif exists(sheet) and not is_writable(sheet):
        # ... ask the user if we should copy the cheatsheet to her home directory for editing
        yes = prompt_yes_or_no(
          'The ' + sheet + ' sheet is not editable. Do you want to copy it to '
          'your user cheatsheets directory before editing? Keep in mind that '
          'your sheet will always be used before system-wide one.'
        )

        # if yes, copy the cheatsheet to the home directory before editing
        if yes:
            copy(path(sheet), os.path.join(sheets.default_path(), sheet))
            edit(sheet)

        # if no, just abort
        else:
            die('Aborting.')


def create(sheet):
    """ Creates a cheatsheet """
    new_sheet_path = os.path.join(sheets.default_path(), sheet)

    try:
        subprocess.call([editor(), new_sheet_path])

    except OSError:
        die('Could not launch ' + editor())


def edit(sheet):
    """ Opens a cheatsheet for editing """

    try:
        subprocess.call([editor(), path(sheet)])

    except OSError:
        die('Could not launch ' + editor())


def exists(sheet):
    """ Predicate that returns true if the sheet exists """
    return sheet in sheets.get() and os.access(path(sheet), os.R_OK)


def is_writable(sheet):
    """ Predicate that returns true if the sheet is writeable """
    return sheet in sheets.get() and os.access(path(sheet), os.W_OK)


def path(sheet):
    """ Returns a sheet's filesystem path """
    return sheets.get()[sheet]


def read(sheet):
    """ Returns the contents of the cheatsheet as a String """
    if not exists(sheet):
        die('No cheatsheet found for ' + sheet)

    with open (path(sheet)) as cheatfile:
          return cheatfile.read()

########NEW FILE########
__FILENAME__ = sheets
from cheat import cheatsheets
from cheat.utils import *
import os

# @kludge: it breaks the functional paradigm to a degree, but declaring this
# var here (versus within get()) gives us a "poor man's" memoization on the
# call to get(). This, in turn, spares us from having to call out to the
# filesystem more than once.
cheats = {}


def default_path():
    """ Returns the default cheatsheet path """

    # the default path becomes confused when cheat is run as root, so fail
    # under those circumstances. (There is no good reason to need to run cheat
    # as root.)
    if os.name != 'nt' and os.geteuid() == 0:
        die('Please do not run this application as root.');

    # determine the default cheatsheet dir
    default_sheets_dir = os.environ.get('DEFAULT_CHEAT_DIR') or os.path.join(os.path.expanduser('~'), '.cheat')

    # create the DEFAULT_CHEAT_DIR if it does not exist
    if not os.path.isdir(default_sheets_dir):
        try:
            # @kludge: unclear on why this is necessary
            os.umask(0000)
            os.mkdir(default_sheets_dir)

        except OSError:
            die('Could not create DEFAULT_CHEAT_DIR')

    # assert that the DEFAULT_CHEAT_DIR is readable and writable
    if not os.access(default_sheets_dir, os.R_OK):
        die('The DEFAULT_CHEAT_DIR (' + default_sheets_dir +') is not readable.')
    if not os.access(default_sheets_dir, os.W_OK):
        die('The DEFAULT_CHEAT_DIR (' + default_sheets_dir +') is not writeable.')

    # return the default dir
    return default_sheets_dir


def get():
    """ Assembles a dictionary of cheatsheets as name => file-path """

    # if we've already reached out to the filesystem, just return the result
    # from memory
    if cheats:
        return cheats

    # otherwise, scan the filesystem
    for cheat_dir in reversed(paths()):
        cheats.update(
            dict([
                (cheat, os.path.join(cheat_dir, cheat))
                for cheat in os.listdir(cheat_dir)
                if not cheat.startswith('.')
                and not cheat.startswith('__')
            ])
        )

    return cheats


def paths():
    """ Assembles a list of directories containing cheatsheets """
    sheet_paths = [
        default_path(),
        cheatsheets.sheets_dir()[0],
    ]

    # merge the CHEATPATH paths into the sheet_paths
    if 'CHEATPATH' in os.environ and os.environ['CHEATPATH']:
        for path in os.environ['CHEATPATH'].split(os.pathsep):
            if os.path.isdir(path):
                sheet_paths.append(path)

    if not sheet_paths:
        die('The DEFAULT_CHEAT_DIR dir does not exist or the CHEATPATH is not set.')

    return sheet_paths


def list():
    """ Lists the available cheatsheets """
    sheet_list = ''
    pad_length = max([len(x) for x in get().keys()]) + 4
    for sheet in sorted(get().items()):
        sheet_list += sheet[0].ljust(pad_length) + sheet[1] + "\n"
    return sheet_list


def search(term):
    """ Searches all cheatsheets for the specified term """
    result = ''

    for cheatsheet in sorted(get().items()):
        match = ''
        for line in open(cheatsheet[1]):
             if term in line:
                  match += '  ' + line

        if not match == '':
            result += cheatsheet[0] + ":\n" + match + "\n"

    return result

########NEW FILE########
__FILENAME__ = utils
import os
import sys


def colorize(sheet_content):
    """ Colorizes cheatsheet content if so configured """

    # only colorize if so configured
    if not 'CHEATCOLORS' in os.environ:
        return sheet_content

    try:
        from pygments import highlight
        from pygments.lexers import BashLexer
        from pygments.formatters import TerminalFormatter

    # if pygments can't load, just return the uncolorized text
    except ImportError:
        return sheet_content

    return highlight(sheet_content, BashLexer(), TerminalFormatter())


def die(message):
    """ Prints a message to stderr and then terminates """
    warn(message)
    exit(1)


def editor():
    """ Determines the user's preferred editor """
    if 'EDITOR' not in os.environ:
        die(
            'In order to create/edit a cheatsheet you must set your EDITOR '
            'environment variable to your editor\'s path.'
        )

    elif os.environ['EDITOR'] == "":
        die(
          'Your EDITOR environment variable is set to an empty string. It must '
          'be set to your editor\'s path.'
        )

    else:
        return os.environ['EDITOR']


def prompt_yes_or_no(question):
    """ Prompts the user with a yes-or-no question """
    print(question)
    return raw_input('[y/n] ') == 'y'


def warn(message):
    """ Prints a message to stderr """
    print >> sys.stderr, (message)

########NEW FILE########
