__FILENAME__ = handler
# vim: set fdm=marker fdc=2 :
# coding=utf-8

# imports {{{1
import vim
import re
from glob import glob
from os import walk
from os.path import join, getmtime, isfile, isdir, exists
from subprocess import Popen, PIPE
from padlib.utils import get_save_dir
from padlib.pad import PadInfo
from padlib.timestamps import natural_timestamp

# globals (caches) {{{1
cached_data = []
cached_timestamps = []
cached_filenames = []


def open_pad(path=None, first_line=""):  # {{{1
    """Creates or opens a note.

    path: a valid path for a note.

    first_line: a string to insert to a new note, if given.
    """
    # we require self.save_dir_set to be set to a valid path
    if get_save_dir() == "":
        vim.command('let tmp = confirm("IMPORTANT:\n'
                'Please set g:pad_dir to a valid path in your vimrc.",'
                ' "OK", 1, "Error")')
        return

    # if no path is provided, we create one using the current time
    if not path:
        path = join(get_save_dir(),
                    PadInfo([first_line]).id + vim.eval("g:pad_default_file_extension"))
    path = path.replace(" ", "\ ")

    if bool(int(vim.eval("g:pad_open_in_split"))):
        if vim.eval('g:pad_position["pads"]') == 'right':
            vim.command("silent! rightbelow"
                    + str(vim.eval("g:pad_window_width")) + "vsplit " + path)
        else:
            vim.command("silent! botright"
                    + str(vim.eval("g:pad_window_height")) + "split " + path)
    else:
        vim.command("silent! edit " + path)

    # we don't keep the buffer when we hide it
    vim.command("set bufhidden=wipe")

    # set the filetype to our default
    if vim.eval('&filetype') in ('', 'conf'):
        vim.command("set filetype=" + vim.eval("g:pad_default_format"))

    # map the local commands
    if bool(int(vim.eval('has("gui_running")'))):
        vim.command("noremap <silent> <buffer> <localleader><delete> :call pad#DeleteThis()<cr>")
    else:
        vim.command("noremap <silent> <buffer> <localleader>dd :call pad#DeleteThis()<cr>")

    vim.command("noremap <silent> <buffer> <localleader>+m :call pad#AddModeline()<cr>")
    vim.command("noremap <silent> <buffer> <localleader>+f :call pad#MoveToFolder()<cr>")
    vim.command("noremap <silent> <buffer> <localleader>-f :call pad#MoveToSaveDir()<cr>")
    vim.command("noremap <silent> <buffer> <localleader>+a :call pad#Archive()<cr>")
    vim.command("noremap <silent> <buffer> <localleader>-a :call pad#Unarchive()<cr>")

    # insert the text in first_line to the buffer, if provided
    if first_line:
        vim.current.buffer.append(first_line, 0)
        vim.command("normal! j")


def listdir_recursive_nohidden(path, archive):  # {{{1
    matches = []
    for root, dirnames, filenames in walk(path, topdown=True):
        for dirname in dirnames:
            if dirname.startswith('.'):
                dirnames.remove(dirname)
            if archive != "!":
                if dirname == "archive":
                    dirnames.remove(dirname)
        matches += [join(root, f) for f in filenames if not f.startswith('.')]
    return matches


def get_filelist(query=None, archive=None):  # {{{1
    """ __get_filelist(query) -> list_of_notes

    Returns a list of notes. If no query is provided, all the valid filenames
    in self.save_dir are returned in a list, otherwise, return the results of
    grep or ack search for query in self.save_dir.
    """
    if not query or query == "":
        files = listdir_recursive_nohidden(get_save_dir(), archive)
    else:
        search_backend = vim.eval("g:pad_search_backend")
        if search_backend == "grep":
            # we use Perl mode for grep (-P), because it is really fast
            command = ["grep", "-P", "-n", "-r", query, get_save_dir() + "/"]
            if archive != "!":
                command.append("--exclude-dir=archive")
        elif search_backend == "ack":
            if vim.eval("executable('ack')") == "1":
                ack_path = "ack"
            else:
                ack_path = "/usr/bin/vendor_perl/ack"
            command = [ack_path, query, get_save_dir() + "/", "--type=text"]
            if archive != "!":
                command.append("--ignore-dir=archive")

        if bool(int(vim.eval("g:pad_search_ignorecase"))):
            command.append("-i")
        command.append("--max-count=1")

        files = [line.split(":")[0]
                for line in Popen(command, stdout=PIPE, stderr=PIPE).
                            communicate()[0].split("\n") if line != '']

        if bool(int(vim.eval("g:pad_query_dirnames"))):
            matching_dirs = filter(isdir, glob(join(get_save_dir(), "*"+ query+"*")))
            for mdir in matching_dirs:
                files.extend(filter(lambda x: x not in files, listdir_recursive_nohidden(mdir, archive)))

    return files

def fill_list(files, queried=False, custom_order=False): # {{{1
    """ Writes the list of notes to the __pad__ buffer.

    files: a list of files to process.

    queried: whether files is the result of a query or not.

    custom_order: whether we should keep the order of the list given (implies queried=True).

    Keeps a cache so we only read the notes when the files have been modified.
    """
    global cached_filenames, cached_timestamps, cached_data

    # we won't want to touch the cache
    if custom_order:
        queried = True

    files = filter(exists, [join(get_save_dir(), f) for f in files])

    timestamps = [getmtime(join(get_save_dir(), f)) for f in files]

    # we will have a new list only on the following cases
    if queried or files != cached_filenames or timestamps != cached_timestamps:
        lines = []
        if not custom_order:
            files = reversed(sorted(files, key=lambda i: getmtime(join(get_save_dir(), i))))
        for pad in files:
            pad_path = join(get_save_dir(), pad)
            if isfile(pad_path):
                with open(join(get_save_dir(), pad)) as pad_file:
                    info = PadInfo(pad_file)
                    if info.isEmpty:
                        if bool(int(vim.eval("g:pad_show_dir"))):
                            tail = info.folder + u'\u2e25 '.encode('utf-8') + "[EMPTY]"
                        else:
                            tail = "[EMPTY]"
                    else:
                        if bool(int(vim.eval("g:pad_show_dir"))):
                            tail = info.folder + u'\u2e25 '.encode('utf-8') + u'\u21b2'.encode('utf-8').join((info.summary, info.body))
                        else:
                            tail = u'\u21b2'.encode('utf-8').join((info.summary, info.body))
                    lines.append(pad + " @ " + tail)
            else:
                pass

        # we only update the cache if we are not queried, to preserve the global cache
        if not queried:
            cached_data = lines
            cached_timestamps = timestamps
            cached_filenames = files

    # update natural timestamps
    def add_natural_timestamp(matchobj):
        id_string = matchobj.group("id")
        mtime = str(int(getmtime(join(get_save_dir(), matchobj.group("id")))*1000000))
        return id_string + " @ " + natural_timestamp(mtime).ljust(19) + " │"

    if not queried: # we use the cache
        lines = [re.sub("(?P<id>^.*?) @", add_natural_timestamp, line) for line in cached_data]
    else: # we use the new values in lines
        lines = [re.sub("(?P<id>^.*?) @", add_natural_timestamp, line) for line in lines]

    # we now show the list
    del vim.current.buffer[:] # clear the buffer
    vim.current.buffer.append(list(lines))
    vim.command("normal! dd")

def display(query, archive): # {{{1
    """ Shows a list of notes.

    query: a string representing a regex search. Can be "".

    Builds a list of files for query and then processes it to show the list in the pad format.
    """
    if get_save_dir() == "":
        vim.command('let tmp = confirm("IMPORTANT:\n'\
                'Please set g:pad_dir to a valid path in your vimrc.", "OK", 1, "Error")')
        return
    pad_files = get_filelist(query, archive)
    if len(pad_files) > 0:
        if vim.eval("bufexists('__pad__')") == "1":
            vim.command("bw __pad__")
        if vim.eval('g:pad_position["list"]') == "right":
            vim.command("silent! rightbelow " + str(vim.eval('g:pad_window_width')) + "vnew __pad__")
        else:
            vim.command("silent! botright " + str(vim.eval("g:pad_window_height")) + "new __pad__")
        fill_list(pad_files, query != "")
        vim.command("set filetype=pad")
        vim.command("setlocal nomodifiable")
    else:
        print "no pads"

def search_pads(): # {{{1
    """ Aks for a query and lists the matching notes.
    """
    if get_save_dir() == "":
        vim.command('let tmp = confirm("IMPORTANT:\n'\
                'Please set g:pad_dir to a valid path in your vimrc.", "OK", 1, "Error")')
        return
    query = vim.eval('input(">>> ")')
    display(query, "")
    vim.command("redraw!")

def global_incremental_search():  # {{{1
    """ Provides incremental search in normal mode without opening the list.
    """
    query = ""
    should_create_on_enter = False

    vim.command("echohl None")
    vim.command('echo ">> "')
    while True:
        raw_char = vim.eval("getchar()")
        if raw_char in ("13", "27"):
            if raw_char == "13":
                if should_create_on_enter:
                    open_pad(first_line=query)
                    vim.command("echohl None")
                else:
                    display(query, True)
            vim.command("redraw!")
            break
        else:
            try:   # if we can convert to an int, we have a regular key
                int(raw_char)   # we bring up an error on nr2char
                last_char = vim.eval("nr2char(" + raw_char + ")")
                query = query + last_char
            except:  # if we don't, we have some special key
                keycode = unicode(raw_char, errors="ignore")
                if keycode == "kb":  # backspace
                    query = query[:-len(last_char)]
        pad_files = get_filelist(query)
        if pad_files != []:
            info = ""
            vim.command("echohl None")
            should_create_on_enter = False
        else:  # we will create a new pad
            info = "[NEW] "
            vim.command("echohl WarningMsg")
            should_create_on_enter = True
        vim.command("redraw")
        vim.command('echo ">> ' + info + query + '"')


########NEW FILE########
__FILENAME__ = list_local
# vim: set fdm=marker fdc=2 :
# coding=utf-8

# imports {{{1
import vim
import re
from os import remove, mkdir
from os.path import join, basename, exists
from shutil import move
from padlib.handler import open_pad, get_filelist, fill_list
from padlib.utils import get_save_dir, make_sure_dir_is_empty


def get_selected_path():  # {{{1
    return join(get_save_dir(), vim.current.line.split(" @")[0])


def edit_pad():  # {{{1
    """ Opens the currently selected note in the __pad__ buffer.
    """
    path = get_selected_path()
    vim.command("bd")
    open_pad(path=path)


def delete_pad():  # {{{1
    """ Deletes the currently selected note in the __pad__ buffer.
    """
    confirm = vim.eval('input("really delete? (y/n): ")')
    if confirm in ("y", "Y"):
        path = get_selected_path()
        remove(path)
        make_sure_dir_is_empty(path)
        vim.command("ListPads")
        vim.command("redraw!")


def move_to_folder(path=None):  # {{{1
    """ Moves the selected pad to a subfolder of g:pad_dir
    """
    selected_path = get_selected_path()
    if path is None:
        path = vim.eval('input("move to: ")')
    if not exists(join(get_save_dir(), path)):
        mkdir(join(get_save_dir(), path))
    move(selected_path, join(get_save_dir(), path, basename(selected_path)))
    make_sure_dir_is_empty(path)
    vim.command("ListPads")
    if path is None:
        vim.command("redraw!")


def move_to_savedir():  # {{{1
    """ Moves a note to g:pad_dir
    """
    move_to_folder("")


def archive_pad():  # {{{1
    """ Archives the currently selected note
    """
    move_to_folder("archive")


def unarchive_pad():  # {{{1
    """ Unarchives the currently selected note
    """
    move_to_savedir()


def incremental_search():  # {{{1
    """ Provides incremental search within the __pad__ buffer.
    """
    query = ""
    should_create_on_enter = False

    vim.command("echohl None")
    vim.command('echo ">> "')
    while True:
        raw_char = vim.eval("getchar()")
        if raw_char in ("13", "27"):
            if raw_char == "13" and should_create_on_enter:
                vim.command("bw")
                open_pad(first_line=query)
                vim.command("echohl None")
            vim.command("redraw!")
            break
        else:
            try:   # if we can convert to an int, we have a regular key
                int(raw_char)   # we bring up an error on nr2char
                last_char = vim.eval("nr2char(" + raw_char + ")")
                query = query + last_char
            except:  # if we don't, we have some special key
                keycode = unicode(raw_char, errors="ignore")
                if keycode == "kb":  # backspace
                    query = query[:-len(last_char)]
        vim.command("setlocal modifiable")
        pad_files = get_filelist(query)
        if pad_files != []:
            fill_list(pad_files, query != "")
            vim.command("setlocal nomodifiable")
            info = ""
            vim.command("echohl None")
            should_create_on_enter = False
        else:  # we will create a new pad
            del vim.current.buffer[:]
            info = "[NEW] "
            vim.command("echohl WarningMsg")
            should_create_on_enter = True
        vim.command("redraw")
        vim.command('echo ">> ' + info + query + '"')
# }}}1
# sort types {{{1
SORT_TYPES = {
        "1": "title",
        "2": "tags",
        "3": "date"
        }


def sort(key="1"):  # {{{1

    if key not in SORT_TYPES:
        return

    key = SORT_TYPES[key]
    if key == "date":
        vim.command("ListPads")
        return

    tuples = []
    if key == "tags":
        view_files = [line.split()[0] for line in vim.current.buffer]
        for pad_id in view_files:
            with open(pad_id) as fi:
                tags = sorted([tag.lower().replace("@", "")
                                for tag in re.findall("@\w*", fi.read(200))])
            tuples.append((pad_id, tags))
        tuples = sorted(tuples, key=lambda f: f[1])
        tuples = filter(lambda i: i[1] != [], tuples) + \
                 filter(lambda i: i[1] == [], tuples)
    elif key == "title":
        l = 1
        for line in vim.current.buffer:
            pad_id = line.split()[0]
            title = vim.eval('''split(split(substitute(getline(''' + str(l) + '''), '↲','\n', "g"), '\n')[0], ' │ ')[1]''')
            tuples.append((pad_id, title))
            l += 1
        tuples = sorted(tuples, key=lambda f: f[1])

    vim.command("setlocal modifiable")
    fill_list([f[0] for f in tuples], custom_order=True)
    vim.command("setlocal nomodifiable")

########NEW FILE########
__FILENAME__ = modelines
html_style = ("<!-- ", " -->")
vim_style = ('" ', '')
hash_style = ("# ", '')

comment_style_map = {
        "markdown": html_style,
        "pandoc": html_style,
        "textile": html_style,
        "vo_base": html_style,
        "quicktask": hash_style
        }


def format_modeline(filetype):
    try:
        style = comment_style_map[filetype]
    except KeyError:
        style = vim_style
    return style[0] + "vim: set ft=" + filetype + ":" + style[1]


########NEW FILE########
__FILENAME__ = pad
import vim
import re
from os.path import abspath, basename
from padlib.timestamps import timestamp
from padlib.utils import get_save_dir


class PadInfo(object):
    __slots__ = "id", "summary", "body", "isEmpty", "folder"

    def __init__(self, source):
        """

        source can be:

        * a vim buffer
        * a file object
        * a list of strings, one per line
        """

        nchars = int(vim.eval("g:pad_read_nchars_from_files"))
        self.summary = ""
        self.body = ""
        self.isEmpty = True
        self.folder = ""
        self.id = timestamp()

        if source is vim.current.buffer:
            source = source[:10]
        elif source.__class__ == file:
            pos = len(get_save_dir()), len(basename(source.name))
            self.folder = abspath(source.name)[pos[0]:-pos[1]]
            source = source.read(nchars).split("\n")

        data = [line.strip() for line in source if line != ""]

        if data != []:
            # we discard modelines
            if re.match("^.* vim: set .*:.*$", data[0]):
                data = data[1:]

            self.summary = data[0].strip()
            # vim-orgmode adds tags after whitespace
            org_tags_data = re.search("\s+(?P<tags>:.*$)", self.summary)
            if org_tags_data:
                self.summary = re.sub("\s+:.*$", "", self.summary)
            if self.summary[0] in ("%", "#"):  # pandoc and markdown titles
                self.summary = str(self.summary[1:]).strip()

            self.body = u'\u21b2'.encode('utf-8').join(data[1:]).strip()
            # if we have orgmode tag data, add it to the body
            if org_tags_data:
                self.body = ' '.join(\
                    [" ".join(\
                              map(lambda a: "@" + a, \
                                  filter(lambda a: a != "", \
                                         org_tags_data.group("tags").split(":")))), \
                     self.body])
            # remove extra spaces in bodies
            self.body = re.sub("\s{2,}", "", self.body)

        if self.summary != "":
            self.isEmpty = False
            self.id = self.summary.lower().replace(" ", "_")
            # remove ilegal characters from names (using rules for windows
            # systems to err on the side of precaution)
            self.id = re.sub("[*:<>/\|^]", "", self.id)

        if self.id.startswith("."):
            self.id = re.sub("^\.*", "", self.id)

########NEW FILE########
__FILENAME__ = pad_local
import vim
from shutil import move
from os import remove, mkdir
from os.path import expanduser, exists, join, splitext, isfile, basename, dirname
from padlib.pad import PadInfo
from padlib.utils import get_save_dir
from padlib.modelines import format_modeline
from glob import glob


def update():
    """ Moves a note to a new location if its contents are modified.

    Called on the BufLeave event for the notes.

    """
    modified = bool(int(vim.eval("b:pad_modified")))
    can_rename = bool(int(vim.eval("g:pad_rename_files")))
    if modified and can_rename:
        _id = PadInfo(vim.current.buffer).id
        old_path = expanduser(vim.current.buffer.name)

        fs = filter(isfile, glob(expanduser(join(dirname(vim.current.buffer.name), _id)) + "*"))
        if old_path not in fs:
            if fs == []:
                new_path = expanduser(join(get_save_dir(), _id))
            else:
                exts = map(lambda i: '0' if i == '' else i[1:],
                                    map(lambda i: splitext(i)[1], fs))
                new_path = ".".join([
                                    expanduser(join(get_save_dir(), _id)),
                                    str(int(max(exts)) + 1)])
            new_path = new_path + vim.eval("g:pad_default_file_extension")
            vim.command("bw")
            move(old_path, new_path)


def delete():
    """ (Local command) Deletes the current note.
    """
    path = vim.current.buffer.name
    if exists(path):
        confirm = vim.eval('input("really delete? (y/n): ")')
        if confirm in ("y", "Y"):
            remove(path)
            vim.command("bd!")
            vim.command("redraw!")


def add_modeline():
    """ (Local command) Add a modeline to the current note.
    """
    mode = vim.eval('input("filetype: ", "", "filetype")')
    if mode:
        args = [format_modeline(mode)]
        if vim.eval('g:pad_modeline_position') == 'top':
            args.append(0)
        vim.current.buffer.append(*args)
        vim.command("set filetype=" + mode)
        vim.command("set nomodified")


def move_to_folder(path=None):
    if path is None:
        path = vim.eval("input('move to: ')")
    new_path = join(get_save_dir(), path, basename(vim.current.buffer.name))
    if not exists(join(get_save_dir(), path)):
        mkdir(join(get_save_dir(), path))
    move(vim.current.buffer.name, new_path)
    vim.command("bd")


def move_to_savedir():
    move_to_folder("")


def archive():
    move_to_folder("archive")


def unarchive():
    move_to_savedir()

########NEW FILE########
__FILENAME__ = timestamps
import time
import datetime
from os.path import basename


def base36encode(number, alphabet='0123456789abcdefghijklmnopqrstuvxxyz'):
    """Convert positive integer to a base36 string."""
    if not isinstance(number, (int, long)):
        raise TypeError('number must be an integer')

    # Special case for zero
    if number == 0:
        return alphabet[0]

    base36 = ''

    sign = ''
    if number < 0:
        sign = '-'
        number = - number

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36


def protect(id):
    """ Prevent filename collisions
    """
    return id + "." + base36encode(int(timestamp()))


def timestamp():
    """timestamp() -> str:timestamp

    Returns a string of digits representing the current time.
    """
    return str(int(time.time() * 1000000))


def natural_timestamp(timestamp):
    """natural_timestamp(str:timestamp) -> str:natural_timestamp

    Returns a string representing a datetime object.

        timestamp: a string in the format returned by pad_timestamp.

    The output uses a natural format for timestamps within the previous
    24 hours, and the format %Y-%m-%d %H:%M:%S otherwise.
    """
    timestamp = basename(timestamp)
    f_timestamp = float(timestamp) / 1000000
    tmp_datetime = datetime.datetime.fromtimestamp(f_timestamp)
    diff = datetime.datetime.now() - tmp_datetime
    days = diff.days
    seconds = diff.seconds
    minutes = seconds / 60
    hours = minutes / 60

    if days > 0:
        return tmp_datetime.strftime("%Y-%m-%d %H:%M:%S")
    if hours < 1:
        if minutes < 1:
            return str(seconds) + "s ago"
        else:
            seconds_diff = seconds - (minutes * 60)
            if seconds_diff != 0:
                return str(minutes) + "m and " + str(seconds_diff) + "s ago"
            else:
                return str(minutes) + "m ago"
    else:
        minutes_diff = minutes - (hours * 60)
        if minutes_diff != 0:
            return str(hours) + "h and " + str(minutes_diff) + "m ago"
        else:
            return str(hours) + "h ago"


########NEW FILE########
__FILENAME__ = utils
import vim
from os import rmdir
from os.path import expanduser, split


def get_save_dir():
    return expanduser(vim.eval("g:pad_dir")).replace("\\", "\\\\")


def make_sure_dir_is_empty(path):  # {{{1
    try:
        rmdir(split(path)[0])
    except:
        pass


########NEW FILE########
__FILENAME__ = vim_globals
# coding=utf-8
import vim
from os.path import join
from padlib.utils import get_save_dir

def set_vim_globals():
    """ Sets global vim preferences and commands.
    """
    # To update the date when files are modified
    if get_save_dir() == "":
        vim.command('let tmp = confirm("IMPORTANT:\n'
                'Please set g:pad_dir to a valid path in your vimrc.",'
                ' "OK", 1, "Error")')
    else:
        vim.command('execute "au! BufEnter" printf("%s*", g:pad_dir) ":let b:pad_modified = 0"')
        vim.command('execute "au! BufWritePre" printf("%s*", g:pad_dir) ":let b:pad_modified = eval(&modified)"')
        vim.command('execute "au! BufLeave" printf("%s*", g:pad_dir) ":call pad#UpdatePad()"')

    # vim-pad pollutes the MRU.vim list quite a lot, if let alone.
    # This should fix that.
    if vim.eval('exists(":MRU")') == "2":
        mru_exclude_files = vim.eval("MRU_Exclude_Files")
        if mru_exclude_files != '':
            tail = "\|" + mru_exclude_files
        else:
            tail = ''
        vim.command("let MRU_Exclude_Files = '^" +
                join(get_save_dir(), ".*") + tail + "'")

    # we forbid writing backups of the notes
    orig_backupskip = vim.eval("&backupskip")
    vim.command("let &backupskip='" +
            ",".join([orig_backupskip, join(get_save_dir(), "*")]) + "'")


########NEW FILE########
