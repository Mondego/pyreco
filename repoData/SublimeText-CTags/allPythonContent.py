__FILENAME__ = ctags
#!/usr/bin/env python

"""A ctags wrapper, parser and sorter"""

import codecs
import re
import os
import sys
import subprocess
import bisect
import mmap

if sys.version_info<(2,7,0):
    from helpers.check_output import check_output
else:
    from subprocess import check_output

"""
Contants
"""

TAGS_RE = re.compile(
    r'(?P<symbol>[^\t]+)\t'
    r'(?P<filename>[^\t]+)\t'
    r'(?P<ex_command>(/.+/|\?.+\?|\d+));"\t'
    r'(?P<type>[^\t\r\n]+)'
    r'(?:\t(?P<fields>.*))?'
)

# column indexes
SYMBOL = 0
FILENAME = 1

MATCHES_STARTWITH = 'starts_with'

PATH_ORDER = [
    'function', 'class', 'struct',
]

PATH_IGNORE_FIELDS = ('file', 'access', 'signature',
                      'language', 'line', 'inherits')

TAG_PATH_SPLITTERS = ('/', '.', '::', ':')


"""
Functions
"""


"""Helper functions"""


def splits(string, *splitters):
    """Split a string on a number of splitters.

    :param string: string to split
    :param splitters: characters to split string on

    :returns: ``string`` split on characters in ``string``"""
    if splitters:
        split = string.split(splitters[0])
        for s in split:
            for c in splits(s, *splitters[1:]):
                yield c
    else:
        if string:
            yield string


"""Tag processing functions"""


def parse_tag_lines(lines, order_by='symbol', tag_class=None, filters=[]):
    """Parse and sort a list of tags.

    Parse and sort a list of tags one by using a combination of regexen and
    Python functions. The end result is a dictionary containing all 'tags' or
    entries found in the list of tags, sorted and filtered in a manner
    specified by the user.

    :param lines: list of tag lines from a tagfile
    :param order_by: element by which the result should be sorted
    :param tag_class: a Class to wrap around the resulting dictionary
    :param filters: filters to apply to resulting dictionary

    :returns: tag object or dictionary containing a sorted, filtered version
        of the original input tag lines
    """
    tags_lookup = {}

    for line in lines:
        skip = False

        if isinstance(line, Tag):  # handle both text and tag objects
            line = line.line

        line = line.rstrip('\r\n')

        search_obj = TAGS_RE.search(line)

        if not search_obj:
            continue

        tag = search_obj.groupdict()  # convert regex search result to dict

        tag = post_process_tag(tag)

        if tag_class is not None:  # if 'casting' to a class
            tag = tag_class(tag)

        # apply filters, filtering out any matching entries
        for f in filters:
            for k, v in list(f.items()):
                if re.match(v, tag[k]):
                    skip = True

        if skip:  # if a filter was matched, ignore line (filter out)
            continue

        tags_lookup.setdefault(tag[order_by], []).append(tag)

    return tags_lookup


def post_process_tag(tag):
    """Process 'EX Command'-related elements of a tag.

    Process all 'EX Command'-related elements. The 'Ex Command' element has
    previously been split into the 'fields', 'type' and 'ex_command' elements.
    Break these down further as seen below::

        =========== = ============= =========================================
        original    > new           meaning/example
        =========== = ============= =========================================
        symbol      > symbol        symbol name (i.e. class, variable)
        filename    > filename      file containing symbol
        .           > tag_path      tuple of (filename, [class], symbol)
        ex_command  > ex_command    line number or regex used to find symbol
        type        > type          type of symbol (i.e. class, method)
        fields      > fields        string of fields
        .           > [field_keys]  list of parsed field keys
        .           > [field_one]   parsed field element one
        .           > [...]         additional parsed field element
        =========== = ============= =========================================

    Example::

        =========== = ============= =========================================
        original    > new           example
        =========== = ============= =========================================
        symbol      > symbol        'getSum'
        filename    > filename      'DemoClass.java'
        .           > tag_path      ('DemoClass.java', 'DemoClass', 'getSum')
        ex_command  > ex_command    '\tprivate int getSum(int a, int b) {'
        type        > type          'm'
        fields      > fields        'class:DemoClass\tfile:'
        .           > field_keys    ['class', 'file']
        .           > class         'DemoClass'
        .           > file          ''
        =========== = ============= =========================================

    :param tag: dict containing the unprocessed tag

    :returns: dict containing the processed tag
    """
    tag.update(process_fields(tag))

    tag['ex_command'] = process_ex_cmd(tag)

    tag.update(create_tag_path(tag))

    return tag


def process_ex_cmd(tag):
    """Process the 'ex_command' element of a tag dictionary.

    Process the ex_command string - a line number or regex used to find symbol
    declaration - by unescaping the regex where used.

    :param tag: dict containing a tag

    :returns: updated 'ex_command' dictionary entry
    """
    ex_cmd = tag.get('ex_command')

    if ex_cmd.isdigit():  # if a line number, do nothing
        return ex_cmd
    else:                 # else a regex, so unescape
        return re.sub(r"\\(\$|/|\^|\\)", r'\1', ex_cmd[2:-2])  # unescape regex


def process_fields(tag):
    """Process the 'field' element of a tag dictionary.

    Process the fields string - a comma-separated string of "key-value" pairs
    - by generating key-value pairs and appending them to the tag dictionary.
    Also append a list of keys for said pairs.

    :param tag: dict containing a tag

    :returns: dict containing the key-value pairs from the field element, plus
        a list of keys for said pairs
    """
    fields = tag.get('fields')

    if not fields:  # do nothing
        return {}

    # split the fields string into a dictionary of key-value pairs
    result = dict(f.split(':', 1) for f in fields.split('\t'))

    # append all keys to the dictionary
    result['field_keys'] = sorted(result.keys())

    return result


def create_tag_path(tag):
    """Create a tag path entry for a tag dictionary.

    Creates a tag path entry for a tag dictionary from the field key-value
    pairs. Uses format::

        [function] [class] [struct] [additional entries] symbol

    Where ``additional entries`` is any field key-value pair not found in
    ``PATH_IGNORE_FIELDS``

    :param tag: dict containing a tag

    :returns: dict containing the 'tag_path' entry
    """
    field_keys = tag.get('field_keys', [])[:]
    fields = []
    tag_path = ''

    # sort field arguments related to path order in correct order
    for field in PATH_ORDER:
        if field in field_keys:
            fields.append(field)
            field_keys.pop(field_keys.index(field))

    # append all remaining field arguments
    fields.extend(field_keys)

    # convert list of fields to dot-joined string, dropping any "ignore" fields
    for field in fields:
        if field not in PATH_IGNORE_FIELDS:
            tag_path += (tag.get(field) + '.')

    # append symbol as last item in string
    tag_path += tag.get('symbol')

    # split string on seperators and append tag filename to resulting list
    splitup = ([tag.get('filename')] +
               list(splits(tag_path, *TAG_PATH_SPLITTERS)))

    # convert list to tuple
    result = {'tag_path': tuple(splitup)}

    return result


"""Tag building/sorting functions"""


def build_ctags(path, tag_file=None, recursive=False, opts=None, cmd=None,
                env=None):
    """Execute the ``ctags`` command using ``Popen``

    :param path: path to file or directory (with all files) to generate
        ctags for.
    :param tag_file: filename to use for the tag file. Defaults to ``tags``
    :param recursive: specify if search should be recursive in directory
        given by path. This overrides filename specified by ``path``
    :param opts: list of additional options to pass to the ctags executable
    :param env: environment variables to be used when executing ``ctags``

    :returns: original ``tag_file`` filename
    """
    # build the CTags command
    if cmd:
        cmd = [cmd]
    else:
        cmd = ['ctags']

    if not os.path.exists(path):
        raise IOError('\'path\' is not at valid directory or file path, or '
                      'is not accessible')

    if os.path.isfile(path):
        cwd = os.path.dirname(path)
    else:
        cwd = path

    if tag_file:
        cmd.append('-f {0}'.format(tag_file))

    if opts:
        if type(opts) == list:
            cmd.extend(opts)
        else:  # *should* be a list, but better safe than sorry
            cmd.append(opts)

    if recursive:  # ignore any file specified in path if recursive set
        cmd.append('-R')
    elif os.path.isfile(path):
        filename = os.path.basename(path)
        cmd.append(filename)
    else:  # search all files in current directory
        cmd.append(os.path.join(path, '*'))

    # workaround for the issue described here:
    #   http://bugs.python.org/issue6689
    if os.name == 'posix':
        cmd = ' '.join(cmd)

    # execute the command
    check_output(cmd, cwd=cwd, shell=True, env=env, stdin=subprocess.PIPE,
                 stderr=subprocess.STDOUT)

    if not tag_file:  # Exuberant ctags defaults to ``tags`` filename.
        tag_file = os.path.join(cwd, 'tags')
    else:
        if os.path.dirname(tag_file) != cwd:
            tag_file = os.path.join(cwd, tag_file)

    # re-sort ctag file in filename order to improve search performance
    resort_ctags(tag_file)

    return tag_file


def resort_ctags(tag_file):
    """Rearrange ctags file for speed.

    Resorts (re-sort) a CTag file in order of file. This improves searching
    performance when searching tags by file as a binary search can be used.

    The algorithm works as so:

        For each line in the tag file
            Read the file name (``file_name``) the tag belongs to
            If not exists, create an empty array and store in the
                dictionary with the file name as key
            Save the line to this list
        Create a new ``[tagfile]_sorted_by_file`` file
        For each key in the sorted dictionary
            For each line in the list indicated by the key
                Split the line on tab character
                Remove the prepending ``.\`` from the ``file_name`` part of
                    the                   tag
                Join the line again and write the ``sorted_by_file`` file

    :param tag_file: The location of the tagfile to be sorted

    :returns: None
    """
    keys = {}

    with codecs.open(tag_file, encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            keys.setdefault(line.split('\t')[FILENAME], []).append(line)

    with codecs.open(tag_file+'_sorted_by_file', 'w', encoding='utf-8', errors='ignore') as fw:
        for k in sorted(keys):
            for line in keys[k]:
                split = line.split('\t')
                split[FILENAME] = split[FILENAME].lstrip('.\\')
                fw.write('\t'.join(split))


"""
Models
"""


class TagElements(dict):
    """Model the entries of a tag file"""
    def __init__(self, *args, **kw):
        """Initialise Tag object"""
        dict.__init__(self, *args, **kw)
        self.__dict__ = self


class Tag(object):
    """Model a tag.

    This exists mainly to enable different types of sorting.
    """
    def __init__(self, line, column=0):
        if isinstance(line, bytes):  # python 3 compatibility
            line = line.decode('utf-8', 'replace')
        self.line = line
        self.column = column

    def __lt__(self, other):
        return self.line.split('\t')[self.column] < other

    def __gt__(self, other):
        return self.line.split('\t')[self.column] > other

    def __getitem__(self, index):
        return self.line.split('\t')[index]


class TagFile(object):
    """Model a tag file.

    This doesn't actually hold a entire tag file, due in part to the sheer
    size of some tag files (> 100 MB files are possible). Instead, it acts
    as a 'wrapper' of sorts around a file, providing functionality like
    searching for a retrieving tags, finding tags based on given criteria
    (prefix, suffix, exact), getting the directory of a tag and so forth.
    """
    def __init__(self, path, column):
        """Initialise object.

        The file indicated by ``path`` must be sorted by values in the column
        indicated by ``column``.

        :param path: path to a tag file
        :param column: column to search on

        :returns: None
        """
        self.path = path
        self.column = column

    def __getitem__(self, index):
        """Provide sequence-type interface to tag file."""
        self.mapped.seek(index)
        result = self.mapped.readline()

        if index != 0:  # handle first line
            result = self.mapped.readline()  # get a complete line

        result = result.strip()

        return Tag(result, self.column)

    def __len__(self):
        """Get size of tag file in bytes"""
        return len(self.mapped)

    def __enter__(self):
        """Open file on enter when using ``with`` keyword"""
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        """Close file on exit when using ``with`` keyword"""
        self.close()

    @property
    def dir(self):
        """Get directory of tag file"""
        return os.path.dirname(self.path)

    def open(self):
        """Open file"""
        self.file_o = codecs.open(self.path, 'r+b', encoding='ascii')
        self.mapped = mmap.mmap(self.file_o.fileno(), 0,
                                access=mmap.ACCESS_READ)

    def close(self):
        """Close file"""
        self.mapped.close()
        self.file_o.close()

    def search(self, exact_match=True, *tags):
        """Search for one or more tags in the tag file.

        Search a tag file for given tags using a binary search.

        :param exact_match: if search should be an exact or partial match

        :returns: matching tags
        """
        if not tags:
            while self.mapped.tell() < self.mapped.size():
                result = Tag(self.mapped.readline().strip(), self.column)
                yield(result)
            return

        for key in tags:
            leftIndex = bisect.bisect_left(self, key)
            if exact_match:
                result = self[leftIndex]
                while result.line and result[result.column] == key:
                    yield(result)
                    result = Tag(self.mapped.readline().strip(), self.column)
            else:
                result = self[leftIndex]
                while result.line and result[result.column].startswith(key):
                    yield(result)
                    result = Tag(self.mapped.readline().strip(), self.column)

    def search_by_suffix(self, suffix):
        """Search for one or more tags with the given suffix in the tag file.

        Search a tag file for given tags with the given suffix, using a linear
        search. Note that this linear search requires the entire file be
        searched making it slow. Hence, it should be avoided if possible.

        :param suffix: suffix to search for

        :returns: matching tags
        """
        for line in self.file_o:
            if line.split('\t')[self.column].endswith(suffix):
                yield Tag(line)
            else:
                continue

    def tag_class(self):
        """Default class to wrap tag in.

        Allows wrapping of a parsed tag dict in a class, so elements can be
        accessed as class variables (i.e. ``class.variable``, rather than
        ``dict['variable'])
        """
        return type('TagElements', (TagElements,), dict(root_dir=self.dir))

    def get_tags_dict(self, *tags, **kw):
        """Return the tags from a tag file as a dict"""
        filters = kw.get('filters', [])
        return parse_tag_lines(self.search(True, *tags),
                               tag_class=self.tag_class(), filters=filters)

    def get_tags_dict_by_suffix(self, suffix, **kw):
        """Return the tags with the given suffix of a tag file as a dict"""
        filters = kw.get('filters', [])
        return parse_tag_lines(self.search_by_suffix(suffix),
                               tag_class=self.tag_class(), filters=filters)

########NEW FILE########
__FILENAME__ = ctagsplugin
#!/usr/bin/env python

"""A ctags plugin for Sublime Text 2/3"""

import functools
import codecs
import locale
import os
import pprint
import re
import string
import threading
import subprocess

from itertools import chain
from operator import itemgetter as iget
from collections import defaultdict, deque

try:
    import sublime
    import sublime_plugin
    from sublime import status_message, error_message
except ImportError:  # running tests
    import sys

    from tests.sublime_fake import sublime
    from tests.sublime_fake import sublime_plugin

    sys.modules['sublime'] = sublime
    sys.modules['sublime_plugin'] = sublime_plugin

if sublime.version().startswith('2'):
    import ctags
    from ctags import (FILENAME, parse_tag_lines, PATH_ORDER, SYMBOL,
                       TagElements, TagFile)
    from helpers.edit import Edit
else:  # safe to assume if not ST2 then ST3
    from CTags import ctags
    from CTags.ctags import (FILENAME, parse_tag_lines, PATH_ORDER, SYMBOL,
                             TagElements, TagFile)
    from CTags.helpers.edit import Edit

"""
Contants
"""

OBJECT_PUNCTUATORS = {
    'class': '.',
    'struct': '::',
    'function': '/',
}

ENTITY_SCOPE = 'entity.name.function, entity.name.type, meta.toc-list'

RUBY_SPECIAL_ENDINGS = '\?|!'

ON_LOAD = sublime_plugin.all_callbacks['on_load']

RE_SPECIAL_CHARS = re.compile(
    '(\\\\|\\*|\\+|\\?|\\||\\{|\\}|\\[|\\]|\\(|\\)|\\^|\\$|\\.|\\#|\\ )')


"""
Functions
"""

"""Helper functions"""


def get_settings():
    """Load settings.

    :returns: dictionary containing settings
    """
    return sublime.load_settings("CTags.sublime-settings")


def get_setting(key, default=None):
    """Load individual setting.

    :param key: setting key to get value for
    :param default: default value to return if no value found

    :returns: value for ``key`` if ``key`` exists, else ``default``
    """
    return get_settings().get(key, default)

setting = get_setting


def escape_regex(s):
    return RE_SPECIAL_CHARS.sub(lambda m: '\\%s' % m.group(1), s)


def select(view, region):
    sel_set = view.sel()
    sel_set.clear()
    sel_set.add(region)
    sublime.set_timeout(functools.partial(view.show_at_center, region), 1)


def in_main(f):
    @functools.wraps(f)
    def done_in_main(*args, **kw):
        sublime.set_timeout(functools.partial(f, *args, **kw), 0)

    return done_in_main


# TODO: allow thread per tag file. That makes more sense.
def threaded(finish=None, msg='Thread already running'):
    def decorator(func):
        func.running = 0

        @functools.wraps(func)
        def threaded(*args, **kwargs):
            def run():
                try:
                    result = func(*args, **kwargs)
                    if result is None:
                        result = ()

                    elif not isinstance(result, tuple):
                        result = (result, )

                    if finish:
                        sublime.set_timeout(
                            functools.partial(finish, args[0], *result), 0)
                finally:
                    func.running = 0
            if not func.running:
                func.running = 1
                t = threading.Thread(target=run)
                t.setDaemon(True)
                t.start()
            else:
                status_message(msg)
        threaded.func = func

        return threaded

    return decorator


def on_load(path=None, window=None, encoded_row_col=True, begin_edit=False):
    """Decorator to open or switch to a file.

    Opens and calls the "decorated function" for the file specified by path,
    or the current file if no path is specified. In the case of the former, if
    the file is open in another tab that tab will gain focus, otherwise the
    file will be opened in a new tab with a requisite delay to allow the file
    to open. In the latter case, the "decorated function" will be called on
    the currently open file.

    :param path: path to a file
    :param window: the window to open the file in
    :param encoded_row_col: the ``sublime.ENCODED_POSITION`` flag for
        ``sublime.Window.open_file``
    :param begin_edit: if editing the file being opened

    :returns: None
    """
    window = window or sublime.active_window()

    def wrapper(f):
        # if no path, tag is in current open file, return that
        if not path:
            return f(window.active_view())
        # else, open the relevant file
        view = window.open_file(os.path.normpath(path), encoded_row_col)

        def wrapped():
            # if editing the open file
            if begin_edit:
                with Edit(view):
                    f(view)
            else:
                f(view)

        # if buffer is still loading, wait for it to complete then proceed
        if view.is_loading():

            class set_on_load():
                callbacks = ON_LOAD

                def __init__(self):
                    # append self to callbacks
                    self.callbacks.append(self)

                def remove(self):
                    # remove self from callbacks, hence disconnecting it
                    self.callbacks.remove(self)

                def on_load(self, view):
                    # on file loading
                    try:
                        wrapped()
                    finally:
                        # disconnect callback
                        self.remove()

            set_on_load()
        # else just proceed (file was likely open already in another tab)
        else:
            wrapped()

    return wrapper


def find_tags_relative_to(path, tag_file):
    """Find the tagfile relative to a file path.

    :param path: path to a file
    :param tag_file: name of tag file

    :returns: path of deepest tag file with name of ``tag_file``
    """
    if not path:
        return None

    dirs = os.path.dirname(os.path.normpath(path)).split(os.path.sep)

    while dirs:
        joined = os.path.sep.join(dirs + [tag_file])

        if os.path.exists(joined) and not os.path.isdir(joined):
            return joined
        else:
            dirs.pop()

    return None


def get_alternate_tags_paths(view, tags_file):
    """Search for additional tag files.

    Search for additional tag files to use, including those define by a
    ``search_paths`` file, the ``extra_tag_path`` setting and the
    ``extra_tag_files`` setting. This is mostly used for including library tag
    files.

    :param view: sublime text view
    :param tags_file: path to a tag file

    :returns: list of valid, existing paths to additional tag files to search
    """
    tags_paths = '%s_search_paths' % tags_file
    search_paths = [tags_file]

    # read and add additional tag file paths from file
    if os.path.exists(tags_paths):
        search_paths.extend(
            codecs.open(tags_paths, encoding='utf-8').read().split('\n'))

    # read and add additional tag file paths from 'extra_tag_paths' setting
    try:
        for (selector, platform), path in setting('extra_tag_paths'):
            if view.match_selector(view.sel()[0].begin(), selector):
                if sublime.platform() == platform:
                    search_paths.append(os.path.join(path, setting('tag_file')))
    except Exception as e:
        print(e)

    if os.path.exists(tags_paths):
        for extrafile in setting('extra_tag_files'):
            search_paths.append(
                os.path.normpath(
                    os.path.join(os.path.dirname(tags_file), extrafile)))

    # ok, didn't find the tags file under the viewed file.
    # let's look in the currently opened folder
    for folder in view.window().folders():
        search_paths.append(
            os.path.normpath(
                os.path.join(folder, setting('tag_file'))))
        for extrafile in setting('extra_tag_files'):
            search_paths.append(
                os.path.normpath(
                    os.path.join(folder, extrafile)))

    # use list instead of set  for keep order
    ret = []
    for p in search_paths:
        if p and (p not in ret) and os.path.exists(p):
            ret.append(p)
    return ret


def get_common_ancestor_folder(path, folders):
    """Get common ancestor for a file and a list of folders.

    :param path: path to file
    :param folders: list of folder paths

    :returns: path to common ancestor for files and folders file
    """
    old_path = ''  # must initialise to nothing due to lack of do...while
    path = os.path.dirname(path)

    while path != old_path:  # prevent continuing past root directory
        matches = [path for x in folders if x.startswith(path)]

        if matches:
            return max(matches)  # in case of multiple matches, return closest

        old_path = path
        path = os.path.dirname(path)  # go up one level

    return path  # return the root directory


"""Scrolling functions"""


def find_with_scope(view, pattern, scope, start_pos=0, cond=True, flags=0):
    max_pos = view.size()

    while start_pos < max_pos:
        f = view.find(pattern, start_pos, flags)

        if not f or view.match_selector(f.begin(), scope) is cond:
            break
        else:
            start_pos = f.end()

    return f


def find_source(view, pattern, start_at, flags=sublime.LITERAL):
    return find_with_scope(view, pattern, 'string',
                           start_at, False, flags)


def follow_tag_path(view, tag_path, pattern):
    regions = [sublime.Region(0, 0)]

    for p in list(tag_path)[1:-1]:
        while True:  # .end() is BUG!
            regions.append(find_source(view, p, regions[-1].begin()))

            if ((regions[-1] in (None, regions[-2]) or
                 view.match_selector(regions[-1].begin(), ENTITY_SCOPE))):
                regions = [r for r in regions if r is not None]
                break

    start_at = max(regions, key=lambda r: r.begin()).begin() - 1

    # find the ex_command pattern
    pattern_region = find_source(
        view, '^' + escape_regex(pattern) + '$', start_at, flags=0)

    if setting('debug'):  # leave a visual trail for easy debugging
        regions = regions + ([pattern_region] if pattern_region else [])
        view.erase_regions('tag_path')
        view.add_regions('tag_path', regions, 'comment', 1)

    return pattern_region.begin() - 1 if pattern_region else None


def scroll_to_tag(view, tag, hook=None):
    @on_load(os.path.join(tag.root_dir, tag.filename))
    def and_then(view):
        do_find = True

        if tag.ex_command.isdigit():
            look_from = view.text_point(int(tag.ex_command)-1, 0)
        else:
            look_from = follow_tag_path(view, tag.tag_path, tag.ex_command)
            if not look_from:
                do_find = False

        if do_find:
            symbol_region = view.find(
                escape_regex(tag.symbol) + r"(?:[^_]|$)", look_from, 0)

        if do_find and symbol_region:
            # Using reversed symbol_region so cursor stays in front of the
            # symbol. - 1 to discard the additional regex part.
            select_region = sublime.Region(
                symbol_region.end() - 1, symbol_region.begin())
            select(view, select_region)
            if not setting('select_searched_symbol'):
                view.run_command('exit_visual_mode')
        else:
            status_message('Can\'t find "%s"' % tag.symbol)

        if hook:
            hook(view)


"""Formatting helper functions"""


def format_tag_for_quickopen(tag, show_path=True):
    """Format a tag for use in quickopen panel.

    :param tag: tag to display in quickopen
    :param show_path: show path to file containing tag in quickopen

    :returns: formatted tag
    """
    format = []
    tag = ctags.TagElements(tag)
    f = ''

    for field in getattr(tag, 'field_keys', []):
        if field in PATH_ORDER:
            punct = OBJECT_PUNCTUATORS.get(field, ' -> ')
            f += string.Template(
                '    %($field)s$punct%(symbol)s').substitute(locals())

    format = [(f or tag.symbol) % tag, tag.ex_command]
    format[1] = format[1].strip()

    if show_path:
        format.insert(1, tag.filename)

    return format


def prepare_for_quickpanel(formatter=format_tag_for_quickopen):
    """Prepare list of matching ctags for the quickpanel.

    :param formatter: formatter function to apply to tag

    :returns: tuple containing tag and formatted string representation of tag
    """
    def compile_lists(sorter):
        args, display = [], []

        for t in sorter():
            display.append(formatter(t))
            args.append(t)

        return args, display

    return compile_lists


"""File collection helper functions"""


def get_rel_path_to_source(path, tag_file, multiple=True):
    """Get relative path from tag_file to source file.

    :param path: path to a source file
    :param tag_file: path to a tag file
    :param multiple: if multiple tag files open

    :returns: list containing relative path from tag_file to source file
    """
    if multiple:
        return []

    tag_dir = os.path.dirname(tag_file)  # get tag directory
    common_prefix = os.path.commonprefix([tag_dir, path])
    relative_path = os.path.relpath(path, common_prefix)

    return [relative_path]


def get_current_file_suffix(path):
    """Get file extension

    :param path: path to a source file

    :returns: file extension for file
    """
    file_prefix, file_suffix = os.path.splitext(path)

    return file_suffix


"""
Sublime Commands
"""

"""JumpPrev Commands"""


class JumpPrev(sublime_plugin.WindowCommand):
    """Provide ``jump_back`` command.

    Command "jumps back" to the previous code point before a tag was navigated
    or "jumped" to.

    This is functionality supported natively by ST3 but not by ST2. It is
    therefore included for legacy purposes.
    """
    buf = deque(maxlen=100)  # virtually a "ring buffer"

    def is_enabled(self):
        # disable if nothing in the buffer
        return len(self.buf) > 0

    def is_visible(self):
        return setting('show_context_menus')

    def run(self):
        if not self.buf:
            return status_message('JumpPrev buffer empty')

        file_name, sel = self.buf.pop()
        self.jump(file_name, sel)

    def jump(self, fn, sel):
        @on_load(fn, begin_edit=True)
        def and_then(view):
            select(view, sel)

    @classmethod
    def append(cls, view):
        """Append a code point to the list"""
        fn = view.file_name()
        if fn:
            sel = [s for s in view.sel()][0]
            cls.buf.append((fn, sel))


"""CTags commands"""


def show_build_panel(view):
    """Handle build ctags command.

    Allows user to select whether tags should be built for the current file,
    a given directory or all open directories.
    """
    display = []

    if view.file_name() is not None:
        if not setting('recursive'):
            display.append(['Open File', view.file_name()])
        else:
            display.append([
                'Open File\'s Directory', os.path.dirname(view.file_name())])

    if len(view.window().folders()) > 0:
        # append option to build for all open folders
        display.append(
            ['All Open Folders', '; '.join(
                ['\'{0}\''.format(os.path.split(x)[1])
                 for x in view.window().folders()])])
        # append options to build for each open folder
        display.extend(
            [[os.path.split(x)[1], x] for x in view.window().folders()])

    def on_select(i):
        if i != -1:
            if display[i][0] == 'All Open Folders':
                paths = view.window().folders()
            else:
                paths = display[i][1:]

            command = setting('command')
            recursive = setting('recursive')
            tag_file = setting('tag_file')
            opts = setting('opts')

            rebuild_tags = RebuildTags(False)
            rebuild_tags.build_ctags(paths, command, tag_file, recursive, opts)

    view.window().show_quick_panel(display, on_select)


def show_tag_panel(view, result, jump_directly):
    """Handle tag navigation command.

    Jump directly to a tag entry, or show a quick panel with a list of
    matching tags
    """
    if result not in (True, False, None):
        args, display = result
        if not args:
            return

        def on_select(i):
            if i != -1:
                JumpPrev.append(view)
                # Work around bug in ST3 where the quick panel keeps focus after
                # selecting an entry.
                # See https://github.com/SublimeText/Issues/issues/39
                view.window().run_command('hide_overlay')
                scroll_to_tag(view, args[i])

        if jump_directly and len(args) == 1:
            on_select(0)
        else:
            view.window().show_quick_panel(display, on_select)


def ctags_goto_command(jump_directly=False):
    """Decorator to goto a ctag entry.

    Allow jump to a ctags entry, directly or otherwise
    """
    def wrapper(f):
        def command(self, edit, **args):
            view = self.view
            tags_file = find_tags_relative_to(
                view.file_name(), setting('tag_file'))

            if not tags_file:
                status_message('Can\'t find any relevant tags file')
                return

            result = f(self, self.view, args, tags_file)
            show_tag_panel(self.view, result, jump_directly)

        return command
    return wrapper


def check_if_building(self, **args):
    """Check if ctags are currently being built"""
    if RebuildTags.build_ctags.func.running:
        error_message('Please wait while tags are built')
        return False
    return True


def compile_filters(view):
    filters = []
    for selector, regexes in list(setting('filters', {}).items()):
        if view.match_selector(view.sel() and view.sel()[0].begin() or 0,
                               selector):
            filters.append(regexes)
    return filters


def compile_definition_filters(view):
    filters = []
    for selector, regexes in list(setting('definition_filters', {}).items()):
        if view.match_selector(view.sel() and view.sel()[0].begin() or 0,
                               selector):
            filters.append(regexes)
    return filters


"""Goto definition under cursor commands"""


class JumpToDefinition:
    """Provider for NavigateToDefinition and SearchForDefinition commands"""
    @staticmethod
    def run(symbol, view, tags_file):
        tags = {}
        for tags_file in get_alternate_tags_paths(view, tags_file):
            with TagFile(tags_file, SYMBOL) as tagfile:
                tags = tagfile.get_tags_dict(
                    symbol, filters=compile_filters(view))
            if tags:
                break

        if not tags:
            return status_message('Can\'t find "%s"' % symbol)

        def_filters = compile_definition_filters(view)

        def pass_def_filter(o):
            for f in def_filters:
                for k, v in list(f.items()):
                    if k in o:
                        if re.match(v, o[k]):
                            return False
            return True

        @prepare_for_quickpanel()
        def sorted_tags():
            p_tags = list(filter(pass_def_filter, tags.get(symbol, [])))
            if not p_tags:
                status_message('Can\'t find "%s"' % symbol)
            p_tags = sorted(p_tags, key=iget('tag_path'))
            return p_tags

        return sorted_tags


class NavigateToDefinition(sublime_plugin.TextCommand):
    """Provider for the ``navigate_to_definition`` command.

    Command navigates to the definition for a symbol in the open file(s) or
    folder(s).
    """
    is_enabled = check_if_building

    def __init__(self, args):
        sublime_plugin.TextCommand.__init__(self, args)
        self.endings = re.compile(RUBY_SPECIAL_ENDINGS)

    def is_visible(self):
        return setting('show_context_menus')

    @ctags_goto_command(jump_directly=True)
    def run(self, view, args, tags_file):
        region = view.sel()[0]
        if region.begin() == region.end():  # point
            region = view.word(region)

            # handle special line endings for Ruby
            language = view.settings().get('syntax')
            endings = view.substr(sublime.Region(region.end(), region.end()+1))

            if 'Ruby' in language and self.endings.match(endings):
                region = sublime.Region(region.begin(), region.end()+1)
        symbol = view.substr(region)

        return JumpToDefinition.run(symbol, view, tags_file)


class SearchForDefinition(sublime_plugin.WindowCommand):
    """Provider for the ``search_for_definition`` command.

    Command searches for definition for a symbol in the open file(s) or
    folder(s).
    """
    is_enabled = check_if_building

    def is_visible(self):
        return setting('show_context_menus')

    def run(self):
        self.window.show_input_panel(
            '', '', self.on_done, self.on_change, self.on_cancel)

    def on_done(self, symbol):
        view = self.window.active_view()
        tags_file = find_tags_relative_to(
            view.file_name(), setting('tag_file'))

        if not tags_file:
            status_message('Can\'t find any relevant tags file')
            return

        result = JumpToDefinition.run(symbol, view, tags_file)
        show_tag_panel(view, result, True)

    def on_change(self, text):
        pass

    def on_cancel(self):
        pass


"""Show Symbol commands"""

tags_cache = defaultdict(dict)


class ShowSymbols(sublime_plugin.TextCommand):
    """Provider for the ``show_symbols`` command.

    Command shows all symbols for the open file(s) or folder(s).
    """
    is_enabled = check_if_building

    def is_visible(self):
        return setting('show_context_menus')

    @ctags_goto_command()
    def run(self, view, args, tags_file):
        if not tags_file:
            return

        multi = args.get('type') == 'multi'
        lang = args.get('type') == 'lang'

        if view.file_name():
            files = get_rel_path_to_source(
                view.file_name(), tags_file, multi)

        if lang:
            suffix = get_current_file_suffix(view.file_name())
            key = suffix
        else:
            key = ','.join(files)

        tags_file = tags_file + '_sorted_by_file'
        base_path = get_common_ancestor_folder(
            view.file_name(), view.window().folders())

        def get_tags():
            with TagFile(tags_file, FILENAME) as tagfile:
                if lang:
                    return tagfile.get_tags_dict_by_suffix(
                        suffix, filters=compile_filters(view))
                elif multi:
                    return tagfile.get_tags_dict(
                        filters=compile_filters(view))
                else:
                    return tagfile.get_tags_dict(
                        *files, filters=compile_filters(view))

        if key in tags_cache[base_path]:
            print('loading symbols from cache')
            tags = tags_cache[base_path][key]
        else:
            print('loading symbols from file')
            tags = get_tags()
            tags_cache[base_path][key] = tags

        print(('loaded [%d] symbols' % len(tags)))

        if not tags:
            if multi:
                sublime.status_message(
                    'No symbols found **FOR CURRENT FOLDERS**; Try Rebuild?')
            else:
                sublime.status_message(
                    'No symbols found **FOR CURRENT FILE**; Try Rebuild?')

        path_cols = (0, ) if len(files) > 1 or multi else ()
        formatting = functools.partial(
            format_tag_for_quickopen, show_path=bool(path_cols))

        @prepare_for_quickpanel(formatting)
        def sorted_tags():
            return sorted(
                chain(*(tags[k] for k in tags)), key=iget('tag_path'))

        return sorted_tags


"""Rebuild CTags commands"""


class RebuildTags(sublime_plugin.TextCommand):
    """Provider for the ``rebuild_tags`` command.

    Command (re)builds tag files for the open file(s) or folder(s), reading
    relevant settings from the settings file.
    """
    def run(self, edit, **args):
        """Handler for ``rebuild_tags`` command"""
        paths = []

        command = setting('command')
        recursive = setting('recursive')
        opts = setting('opts')
        tag_file = setting('tag_file')

        if 'dirs' in args and args['dirs']:
            paths.extend(args['dirs'])
            self.build_ctags(paths, command, tag_file, recursive, opts)
        elif 'files' in args and args['files']:
            paths.extend(args['files'])
            # build ctags and ignore recursive flag - we clearly only want
            # to build them for a file
            self.build_ctags(paths, command, tag_file, False, opts)
        elif (self.view.file_name() is None and
                len(self.view.window().folders()) <= 0):
            status_message('Cannot build CTags: No file or folder open.')
            return
        else:
            show_build_panel(self.view)

    @threaded(msg='Already running CTags!')
    def build_ctags(self, paths, command, tag_file, recursive, opts):
        """Build tags for the open file or folder(s)

        :param paths: paths to build ctags for
        :param command: ctags command
        :param tag_file: filename to use for the tag file. Defaults to ``tags``
        :param recursive: specify if search should be recursive in directory
            given by path. This overrides filename specified by ``path``
        :param opts: list of additional parameters to pass to the ``ctags``
            executable

        :returns: None
        """
        def tags_building(tag_file):
            """Display 'Building CTags' message in all views"""
            print(('Building CTags for %s: Please be patient' % tag_file))
            in_main(lambda: status_message('Building CTags for {0}: Please be'
                                           ' patient'.format(tag_file)))()

        def tags_built(tag_file):
            """Display 'Finished Building CTags' message in all views"""
            print(('Finished building %s' % tag_file))
            in_main(lambda: status_message('Finished building {0}'
                                           .format(tag_file)))()
            in_main(lambda: tags_cache[os.path.dirname(tag_file)].clear())()

        for path in paths:
            tags_building(path)

            try:
                result = ctags.build_ctags(path=path, tag_file=tag_file,
                                           recursive=recursive, opts=opts,
                                           cmd=command)
            except IOError as e:
                error_message(e.strerror)
                return
            except subprocess.CalledProcessError as e:
                if sublime.platform() == 'windows':
                    str_err = ' '.join(
                        e.output.decode('windows-1252').splitlines())
                else:
                    str_err = e.output.decode(locale.getpreferredencoding()).rstrip()

                error_message(str_err)
                return
            except Exception as e:
                error_message("An unknown error occured.\nCheck the console for info.")
                raise e

            tags_built(result)

        GetAllCTagsList.ctags_list = []  # clear the cached ctags list


"""Autocomplete commands"""


class GetAllCTagsList():
    ctags_list = []

    """cache all the ctags list"""
    def __init__(self, list):
        self.ctags_list = list


class CTagsAutoComplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        if setting('autocomplete'):
            prefix = prefix.strip().lower()
            tags_path = view.window().folders()[0] + '/' + setting('tag_file')

            sub_results = [v.extract_completions(prefix)
                           for v in sublime.active_window().views()]
            sub_results = [(item, item) for sublist in sub_results
                           for item in sublist]  # flatten

            if GetAllCTagsList.ctags_list:
                results = [sublist for sublist in GetAllCTagsList.ctags_list
                           if sublist[0].lower().startswith(prefix)]
                results = sorted(set(results).union(set(sub_results)))

                return results
            else:
                tags = []

                # check if a project is open and the tags file exists
                if not (view.window().folders() and os.path.exists(tags_path)):
                    return tags

                if sublime.platform() == "windows":
                    prefix = ""
                else:
                    prefix = "\\"

                f = os.popen("awk \"{ print "+prefix+"$1 }\" \"" + tags_path + "\"")

                for i in f.readlines():
                    tags.append([i.strip()])

                tags = [(item, item) for sublist in tags
                        for item in sublist]  # flatten
                tags = sorted(set(tags))  # make unique
                GetAllCTagsList.ctags_list = tags
                results = [sublist for sublist in GetAllCTagsList.ctags_list
                           if sublist[0].lower().startswith(prefix)]
                results = list(set(results).union(set(sub_results)))
                results.sort()

                return results


"""Test CTags commands"""


class TestCtags(sublime_plugin.TextCommand):
    routine = None

    def run(self, edit, **args):
        if self.routine is None:
            self.routine = self.co_routine(self.view)
            next(self.routine)

    def __next__(self):
        try:
            next(self.routine)
        except Exception as e:
            print(e)
            self.routine = None

    def co_routine(self, view):
        tag_file = find_tags_relative_to(
            view.file_name(), setting('tag_file'))

        with codecs.open(tag_file, encoding='utf-8') as tf:
            tags = parse_tag_lines(tf, tag_class=TagElements)

        print('Starting Test')

        ex_failures = []
        line_failures = []

        for symbol, tag_list in list(tags.items()):
            for tag in tag_list:
                tag.root_dir = os.path.dirname(tag_file)

                def hook(av):
                    test_context = av.sel()[0]

                    if tag.ex_command.isdigit():
                        test_string = tag.symbol
                    else:
                        test_string = tag.ex_command
                        test_context = av.line(test_context)

                    if not av.substr(test_context).startswith(test_string):
                        failure = 'FAILURE %s' % pprint.pformat(tag)
                        failure += av.file_name()

                        if setting('debug'):
                            if not sublime.question_box('%s\n\n\n' % failure):
                                self.routine = None

                            return sublime.set_clipboard(failure)
                        ex_failures.append(tag)
                    sublime.set_timeout(self.__next__, 5)
                scroll_to_tag(view, tag, hook)
                yield

        failures = line_failures + ex_failures
        tags_tested = sum(len(v) for v in list(tags.values())) - len(failures)

        view = sublime.active_window().new_file()

        with Edit(view) as edit:
            edit.insert(view.size(), '%s Tags Tested OK\n' % tags_tested)
            edit.insert(view.size(), '%s Tags Failed' % len(failures))

        view.set_scratch(True)
        view.set_name('CTags Test Results')

        if failures:
            sublime.set_clipboard(pprint.pformat(failures))

########NEW FILE########
__FILENAME__ = check_output
#!/usr/bin/env python

# Based on source from here: https://gist.github.com/edufelipe/1027906

"""Backport version of 'subprocess.check_output' for Python 2.6.x"""

import subprocess

def check_output(*popenargs, **kwargs):
  r"""Run command with arguments and return its output as a byte string.

  Backported from Python 2.7 as it's implemented as pure python on stdlib.

  >>> check_output(['/usr/bin/python', '--version'])
  Python 2.6.2
  """
  process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
  output, unused_err = process.communicate()
  retcode = process.poll()
  if retcode:
    cmd = kwargs.get("args")
    if cmd is None:
      cmd = popenargs[0]
      error = subprocess.CalledProcessError(retcode, cmd)
      error.output = output
      raise error
  return output

########NEW FILE########
__FILENAME__ = edit
#!/usr/bin/env python

# Copyright, SublimeXiki project <https://github.com/lunixbochs/SublimeXiki>

"""Buffer editing for both ST2 and ST3 that 'just works'"""

import inspect
import sublime
import sublime_plugin

try:
    sublime.edit_storage
except AttributeError:
    sublime.edit_storage = {}


def run_callback(func, *args, **kwargs):
    spec = inspect.getfullargspec(func)
    if spec.args or spec.varargs:
        func(*args, **kwargs)
    else:
        func()


class EditFuture:
    def __init__(self, func):
        self.func = func

    def resolve(self, view, edit):
        return self.func(view, edit)


class EditStep:
    def __init__(self, cmd, *args):
        self.cmd = cmd
        self.args = args

    def run(self, view, edit):
        if self.cmd == 'callback':
            return run_callback(self.args[0], view, edit)

        funcs = {
            'insert': view.insert,
            'erase': view.erase,
            'replace': view.replace,
        }
        func = funcs.get(self.cmd)
        if func:
            args = self.resolve_args(view, edit)
            func(edit, *args)

    def resolve_args(self, view, edit):
        args = []
        for arg in self.args:
            if isinstance(arg, EditFuture):
                arg = arg.resolve(view, edit)
            args.append(arg)
        return args


class Edit:
    def __init__(self, view):
        self.view = view
        self.steps = []

    def __nonzero__(self):
        return bool(self.steps)

    @classmethod
    def future(self, func):
        return EditFuture(func)

    def step(self, cmd, *args):
        step = EditStep(cmd, *args)
        self.steps.append(step)

    def insert(self, point, string):
        self.step('insert', point, string)

    def erase(self, region):
        self.step('erase', region)

    def replace(self, region, string):
        self.step('replace', region, string)

    def sel(self, start, end=None):
        if end is None:
            end = start
        self.step('sel', start, end)

    def callback(self, func):
        self.step('callback', func)

    def run(self, view, edit):
        for step in self.steps:
            step.run(view, edit)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        view = self.view
        if sublime.version().startswith('2'):
            edit = view.begin_edit()
            self.run(view, edit)
            view.end_edit(edit)
        else:
            key = str(hash(tuple(self.steps)))
            sublime.edit_storage[key] = self.run
            view.run_command('apply_edit', {'key': key})


class apply_edit(sublime_plugin.TextCommand):
    def run(self, edit, key):
        sublime.edit_storage.pop(key)(self.view, edit)

########NEW FILE########
__FILENAME__ = sublime_fake
class sublime(object):

    '''Constants'''

    LITERAL = ''
    VERSION = '2.0'

    '''Functions'''

    def load_settings(self, **kargs):
        pass

    @staticmethod
    def version():
        return sublime.VERSION


class sublime_plugin(object):

    '''Constants'''

    all_callbacks = {
        'on_load': []
    }

    '''Classes'''

    class WindowCommand(object):
        pass

    class TextCommand(object):
        pass

    class EventListener(object):
        pass

########NEW FILE########
__FILENAME__ = test_ctags
#!/usr/bin/env python

"""Unit tests for ctags.py"""

import os
import sys
import tempfile
import codecs
from subprocess import CalledProcessError

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

try:
    import sublime

    if int(sublime.version()) > 3000:
        from . import ctags
    else:
        import ctags
except:
    import ctags


class CTagsTest(unittest.TestCase):
    """
    Helper functions
    """

    def build_python_file(self):
        """Build a simple Python "program" that ctags can use.

        :Returns:
        Path to a constructed, valid Python source file
        """
        path = ''

        # the file created here is locked while open, hence we can't delete
        # similarly, ctags appears to require an extension hence the suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix='.py') as temp:
            try:
                path = temp.name  # store name for later use
                temp.writelines([
                    b'def my_definition():\n',
                    b'\toutput = "Hello, world!"\n',
                    b'\tprint(output)\n'])
            finally:
                temp.close()

        return path

    def build_python_file__extended(self):
        """Build a Python "program" demonstrating all common CTag types

        Build a Python program that demonstrates the following CTag types:
            - ``f`` - function definitions
            - ``v`` - variable definitions
            - ``c`` - classes
            - ``m`` - class, struct, and union members
            - ``i`` - import

        This is mainly intended to regression test for issue #209.

        :Returns:
        Path to a constructed, valid Python source file
        """
        path = ''

        # the file created here is locked while open, hence we can't delete
        # similarly, ctags appears to require an extension hence the suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix='.py') as temp:
            try:
                path = temp.name  # store name for later use
                temp.writelines([
                    b'import os\n',
                    b'\n',
                    b'COLOR_RED = "\\c800080FF;"\t#red\n',
                    b'\n',
                    b'def my_function(first_name):\n',
                    b'\tprint("Hello {0}".format(first_name))\n',
                    b'\n',
                    b'class MyClass(object):\n',
                    b'\tlast_name = None\n',
                    b'\taddress = None\t# comment preceded by a tab\n',
                    b'\n',
                    b'\tdef my_method(self, last_name):\n',
                    b'\t\tself.last_name = last_name\n',
                    b'\t\tprint("Hello again, {0}".format(self.last_name))\n'])
            finally:
                temp.close()

        return path

    def build_java_file(self):
        """Build a slightly detailed Java "program" that ctags can use.

        Build a slightly more detailed program that 'build_python_file' does,
        in order to test more advanced functionality of ctags.py, or ctags.exe

        :Returns:
        Path to a constructed, valid Java source file
        """
        path = ''

        # the file created here is locked while open, hence we can't delete
        # similarly, ctags appears to require an extension hence the suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix='.java') as temp:
            try:
                path = temp.name  # store name for later use
                temp.writelines([
                    b'public class DemoClass {\n',
                    b'\tpublic static void main(String args[]) {\n',
                    b'\t\tSystem.out.println("Hello, World");\n',
                    b'\n',
                    b'\t\tDemoClass demo = new DemoClass();\n',
                    b'\t\tSystem.out.printf("Sum %d\n", demo.getSum(5,6));\n',
                    b'\t}\n',
                    b'\n',
                    b'\tprivate int getSum(int a, int b) {\n',
                    b'\t\treturn (a + b);\n',
                    b'\t}\n',
                    b'}\n'])
            finally:
                temp.close()

        return path

    def build_c_file(self):
        """Build a simple C "program" that ctags can use.

        This is mainly intended to regression test for issue #213.

        :Returns:
        Path to a constructed, valid Java source file
        """
        path = ''

        # the file created here is locked while open, hence we can't delete
        # similarly, ctags appears to require an extension hence the suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix='.c') as temp:
            try:
                path = temp.name  # store name for later use
                temp.writelines([
                    b'#define foo(x,y) x+y\n'
                    b'#define foobar 1\n'
                    b'\n'
                    b'void bar()\n'
                    b'{\n'
                    b'\tfoo(10,2);'
                    b'\n'
                    b'#if foobar\n'
                    b'\tfoo(2,3); \n'
                    b'}\n'])
            finally:
                temp.close()

        return path


    """
    Test functions
    """

    def setUp(self):
        """Set up test environment.

        Ensures the ``ctags_not_on_path`` test is run first, and all other
        tests are skipped if this fails. If ctags is not installed, no test
        will pass
        """
        self.test_build_ctags__ctags_on_path()

    """build ctags"""

    def test_build_ctags__ctags_on_path(self):
        """Checks that ``ctags`` is in ``PATH``"""
        # build_ctags requires a real path, so we create a temporary file as a
        # cross-platform way to get the temp directory
        with tempfile.NamedTemporaryFile() as temp:
            try:
                ctags.build_ctags(path=temp.name)
            except EnvironmentError:
                self.fail('build_ctags() raised EnvironmentError. ctags not'
                          ' on path')

    def test_build_ctags__custom_command(self):
        """Checks for support of simple custom command to execute ctags"""
        # build_ctags requires a real path, so we create a temporary file as a
        # cross-platform way to get the temp directory
        with tempfile.NamedTemporaryFile() as temp:
            try:
                ctags.build_ctags(path=temp.name, cmd='ctags')
            except EnvironmentError:
                self.fail('build_ctags() raised EnvironmentError. ctags not'
                          ' on path')

    def test_build_ctags__invalid_custom_command(self):
        """Checks for failure for invalid custom command to execute ctags"""
        # build_ctags requires a real path, so we create a temporary file as a
        # cross-platform way to get the temp directory
        with tempfile.NamedTemporaryFile() as temp:
            with self.assertRaises(CalledProcessError):
                ctags.build_ctags(path=temp.name, cmd='ccttaaggss')

    def test_build_ctags__single_file(self):
        """Test execution of ctags using a single temporary file"""
        path = self.build_python_file()

        tag_file = ctags.build_ctags(path=path)

        with codecs.open(tag_file, encoding='utf-8') as output:
            try:
                content = output.readlines()
                filename = os.path.basename(path)
                self.assertEqual(
                    content[-1],
                    'my_definition\t{0}\t/^def my_definition()'
                    ':$/;"\tf{1}'.format(filename, os.linesep))
            finally:
                output.close()
                os.remove(path)  # clean up
                os.remove(tag_file)

    def test_build_ctags__custom_tag_file(self):
        """Test execution of ctags using a custom tag file"""
        path = self.build_python_file()

        tag_file = ctags.build_ctags(path=path, tag_file='my_tag_file')

        with codecs.open(tag_file, encoding='utf-8') as output:
            try:
                content = output.readlines()
                filename = os.path.basename(path)
                self.assertEqual(
                    content[-1],
                    'my_definition\t{0}\t/^def my_definition()'
                    ':$/;"\tf{1}'.format(filename, os.linesep))
            finally:
                output.close()
                os.remove(path)  # clean up
                os.remove(tag_file)

    def test_build_ctags__additional_options(self):
        """Test execution of ctags using additional ctags options"""
        path = self.build_python_file()

        tag_file = ctags.build_ctags(path=path, tag_file='my_tag_file',
                                     opts="--language-force=java")

        with codecs.open(tag_file, encoding='utf-8') as output:
            try:
                content = output.readlines()
                # there should be nothing in the file but headers (due to the
                # Java 'language-force' option on a Python file)
                self.assertEqual(
                    content[-1][:2],  # all comments start with '!_' - confirm
                    '!_')
            finally:
                output.close()
                os.remove(path)  # clean up
                os.remove(tag_file)

    """post_process_tag"""

    def test_post_process_tag__line_numbers(self):
        """Test ``post_process_tag`` with a line number ``excmd`` variable.

        Test function with an sample tag from a Python file. This in turn tests
        the supporting functions.
        """
        tag = {
            'symbol': 'acme_function',
            'filename': '.\\a_folder\\a_script.py',
            'ex_command': '99',
            'type': 'f',
            'fields': None}

        expected_output = {
            'symbol': 'acme_function',
            'filename': '.\\a_folder\\a_script.py',
            'tag_path': ('.\\a_folder\\a_script.py', 'acme_function'),
            'ex_command': '99',
            'type': 'f',
            'fields': None}

        result = ctags.post_process_tag(tag)

        self.assertEqual(result, expected_output)

    def test_post_process_tag__regex_no_fields(self):
        """Test ``post_process_tag`` with a regex ``excmd`` variable.

        Test function with an sample tag from a Python file. This in turn tests
        the supporting functions.
        """
        tag = {
            'symbol': 'acme_function',
            'filename': '.\\a_folder\\a_script.py',
            'ex_command': '/^def acme_function(tag):$/',
            'type': 'f',
            'fields': None}

        expected_output = {
            'symbol': 'acme_function',
            'filename': '.\\a_folder\\a_script.py',
            'tag_path': ('.\\a_folder\\a_script.py', 'acme_function'),
            'ex_command': 'def acme_function(tag):',
            'type': 'f',
            'fields': None}

        result = ctags.post_process_tag(tag)

        self.assertEqual(result, expected_output)

    def test_post_process_tag__fields(self):
        """Test ``post_process_tag`` with a number of ``field`` variables.

        Test function with an sample tag from a Java file. This in turn tests
        the supporting functions.
        """
        tag = {
            'symbol': 'getSum',
            'filename': '.\\a_folder\\DemoClass.java',
            'ex_command': '/^\tprivate int getSum(int a, int b) {$/',
            'type': 'm',
            'fields': 'class:DemoClass\tfile:'}

        expected_output = {
            'symbol': 'getSum',
            'filename': '.\\a_folder\\DemoClass.java',
            'tag_path': ('.\\a_folder\\DemoClass.java', 'DemoClass', 'getSum'),
            'ex_command': '\tprivate int getSum(int a, int b) {',
            'type': 'm',
            'fields': 'class:DemoClass\tfile:',
            'field_keys': ['class', 'file'],
            'class': 'DemoClass',
            'file': ''}

        result = ctags.post_process_tag(tag)

        self.assertEqual(result, expected_output)


    """Tag class"""

    def test_parse_tag_lines__python(self):
        """Test ``parse_tag_lines`` with a sample Python file"""
        path = self.build_python_file__extended()

        tag_file = ctags.build_ctags(path=path, opts=['--python-kinds=-i'])

        with codecs.open(tag_file, encoding='utf-8') as output:
            try:
                content = output.readlines()
                filename = os.path.basename(path)
            except:
                self.fail("Setup of files for test failed")
            finally:
                output.close()
                os.remove(path)  # clean up
                os.remove(tag_file)

        expected_outputs = {
            'MyClass': [{
                'symbol': 'MyClass',
                'filename': filename,
                'ex_command': 'class MyClass(object):',
                'tag_path': (filename, 'MyClass'),
                'type': 'c',
                'fields': None}],
            'address': [{
                'symbol': 'address',
                'filename': filename,
                'ex_command': '\taddress = None\t# comment preceded by a tab',
                'tag_path': (filename, 'MyClass', 'address'),
                'type': 'v',
                'fields': 'class:MyClass',
                'field_keys': ['class'],
                'class': 'MyClass'}],
            'last_name': [{
                'symbol': 'last_name',
                'filename': filename,
                'ex_command': '\tlast_name = None',
                'tag_path': (filename, 'MyClass', 'last_name'),
                'type': 'v',
                'fields': 'class:MyClass',
                'field_keys': ['class'],
                'class': 'MyClass'}],
            'my_function': [{
                'symbol': 'my_function',
                'filename': filename,
                'ex_command': 'def my_function(first_name):',
                'tag_path': (filename, 'my_function'),
                'type': 'f',
                'fields': None}],
            'my_method': [{
                'symbol': 'my_method',
                'filename': filename,
                'ex_command': '\tdef my_method(self, last_name):',
                'tag_path': (filename, 'MyClass', 'my_method'),
                'type': 'm',
                'fields': 'class:MyClass',
                'field_keys': ['class'],
                'class': 'MyClass'}],
            'COLOR_RED': [{
                'symbol': 'COLOR_RED',
                'filename': filename,
                'ex_command': 'COLOR_RED = "\\c800080FF;"\t#red',
                'tag_path': (filename, 'COLOR_RED'),
                'type': 'v',
                'fields': None}],
            }

        result = ctags.parse_tag_lines(content)

        for key in expected_outputs:
            self.assertEqual(result[key], expected_outputs[key])

        for key in result:  # don't forget - we might have missed something!
            self.assertEqual(expected_outputs[key], result[key])

    def test_parse_tag_lines__c(self):
        """Test ``parse_tag_lines`` with a sample C file"""
        path = self.build_c_file()

        tag_file = ctags.build_ctags(path=path)

        with codecs.open(tag_file, encoding='utf-8') as output:
            try:
                content = output.readlines()
                filename = os.path.basename(path)
            except IOError:
                self.fail("Setup of files for test failed")
            finally:
                output.close()
                os.remove(path)  # clean up
                os.remove(tag_file)

        expected_outputs = {
            'bar': [{
                'symbol': 'bar',
                'filename': filename,
                'ex_command': 'void bar()',
                'tag_path': (filename, 'bar'),
                'type': 'f',
                'fields': None}],
            'foo': [{
                'symbol': 'foo',
                'filename': filename,
                'ex_command': '1',
                'tag_path': (filename, 'foo'),
                'type': 'd',
                'fields': 'file:',
                'field_keys': ['file'],
                'file': ''}],
            'foobar': [{
                'symbol': 'foobar',
                'filename': filename,
                'ex_command': '2',
                'tag_path': (filename, 'foobar'),
                'type': 'd',
                'fields': 'file:',
                'field_keys': ['file'],
                'file': ''}]
            }

        result = ctags.parse_tag_lines(content)

        for key in expected_outputs:
            self.assertEqual(result[key], expected_outputs[key])

        for key in result:  # don't forget - we might have missed something!
            self.assertEqual(expected_outputs[key], result[key])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_ctagsplugin
#!/usr/bin/env python

"""Unit tests for ctagsplugin.py"""

import os
import sys
import tempfile
import shutil

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

try:
    import sublime

    if int(sublime.version()) > 3000:
        from . import ctagsplugin
        from . import ctags
    else:
        import ctagsplugin
        import ctags
except:
    import ctagsplugin
    import ctags


class CTagsPluginTest(unittest.TestCase):

    """
    Helper functions
    """

    def make_tmp_directory(self, pwd=None):
        """Make a temporary directory to place files in

        :returns: Path to the temporary directory
        """
        tmp_dir = tempfile.mkdtemp(dir=pwd)
        return tmp_dir

    def build_python_file(self, pwd=None):
        """Build a simple Python "program" that ctags can use.

        :Returns:
        Path to a constructed, valid Java source file
        """
        path = ''

        # the file created here is locked while open, hence we can't delete
        # similarly, ctags appears to require an extension hence the suffix
        with tempfile.NamedTemporaryFile(
                delete=False, suffix='.py', dir=pwd) as temp:
            try:
                path = temp.name  # store name for later use
                temp.writelines([
                    b'def my_definition():\n',
                    b'\toutput = "Hello, world!"\n',
                    b'\tprint(output)\n'])
            finally:
                temp.close()

        return path

    def build_java_file(self, pwd=None):
        """Build a slightly detailed Java "program" that ctags can use.

        Build a slightly more detailed program that 'build_python_file' does,
        in order to test more advanced functionality of ctags.py, or ctags.exe

        :Returns:
        Path to a constructed, valid Java source file
        """
        path = ''

        # the file created here is locked while open, hence we can't delete
        # similarly, ctags appears to require an extension hence the suffix
        with tempfile.NamedTemporaryFile(
                delete=False, suffix='.java', dir=pwd) as temp:
            try:
                path = temp.name  # store name for later use
                temp.writelines([
                    b'public class DemoClass {\n',
                    b'\tpublic static void main(String args[]) {\n',
                    b'\t\tSystem.out.println("Hello, World");\n',
                    b'\n',
                    b'\t\tDemoClass demo = new DemoClass();\n',
                    b'\t\tSystem.out.printf("Sum %d\n", demo.getSum(5,6));\n',
                    b'\t}\n',
                    b'\n',
                    b'\tprivate int getSum(int a, int b) {\n',
                    b'\t\treturn (a + b);\n',
                    b'\t}\n',
                    b'}\n'])
            finally:
                temp.close()

        return path

    def remove_tmp_directory(self, path):
        """Remove a temporary directory made by ``make_tmp_directory``

        :param path: Path to directory

        :returns: True if directory deleted, else False
        """
        shutil.rmtree(path)

    def remove_tmp_files(self, paths):
        """Remove temporary files made by ``make_x_file``

        :param paths: Path to file

        :returns: True if file deleted, else False
        """
        for path in paths:
            os.remove(path)

    """
    Test functions
    """

    """find_tags_relative_to"""

    def test_find_tags_relative_to__find_tags_in_current_directory(self):
        TAG_FILE = 'example_tags'

        current_path = self.build_python_file()
        tag_file = ctags.build_ctags(path=current_path, tag_file=TAG_FILE)

        # should find tag file in current directory
        self.assertEqual(
            ctagsplugin.find_tags_relative_to(current_path, TAG_FILE),
            tag_file)

        # cleanup
        self.remove_tmp_files([current_path, tag_file])

    def test_find_tags_relative_to__find_tags_in_parent_directory(self):
        TAG_FILE = 'example_tags'

        parent_path = self.build_python_file()
        parent_tag_file = ctags.build_ctags(path=parent_path,
                                            tag_file=TAG_FILE)
        child_dir = self.make_tmp_directory()
        child_path = self.build_python_file(pwd=child_dir)

        # should find tag file in parent directory
        self.assertEqual(
            ctagsplugin.find_tags_relative_to(child_path, TAG_FILE),
            parent_tag_file)

        # cleanup
        self.remove_tmp_files([parent_path, parent_tag_file])
        self.remove_tmp_directory(child_dir)

    """get_common_ancestor_folder"""

    def test_get_common_ancestor_folder__current_folder_open(self):
        parent_dir = '/c/users'

        temp = parent_dir + '/example.py'

        path = ctagsplugin.get_common_ancestor_folder(temp, [parent_dir])

        # should return parent of the two child directories the deepest common
        # folder
        self.assertEqual(path, parent_dir)

    def test_get_common_ancestor_folder__single_ancestor_folder_open(self):
        parent_dir = '/c/users'
        child_dir = parent_dir + '/child'

        temp = child_dir + '/example.py'

        path = ctagsplugin.get_common_ancestor_folder(temp, [parent_dir])

        # should return parent of the two child directories the deepest common
        # folder
        self.assertEqual(path, parent_dir)

    def test_get_common_ancestor_folder__single_sibling_folder_open(self):
        parent_dir = '/c/users'
        child_a_dir = parent_dir + '/child_a'
        child_b_dir = parent_dir + '/child_b'

        temp = child_b_dir + '/example.py'

        path = ctagsplugin.get_common_ancestor_folder(temp, [child_a_dir])

        # should return parent of the two child directories the deepest common
        # folder
        self.assertEqual(path, parent_dir)

    def test_get_common_ancestor_folder__single_child_folder_open(self):
        parent_dir = '/c/users'
        child_dir = parent_dir + '/child'
        grandchild_dir = child_dir + '/grandchild'

        temp = child_dir + '/example.py'

        # create temporary folders and files
        path = ctagsplugin.get_common_ancestor_folder(temp, [grandchild_dir])

        # should return child directory as the deepest common folder
        self.assertEqual(path, child_dir)

    """get_rel_path_to_source"""

    def test_get_rel_path_to_source__source_file_in_sibling_directory(self):
        temp = '/c/users/temporary_file'
        tag_file = '/c/users/tags'

        result = ctagsplugin.get_rel_path_to_source(
            temp, tag_file, multiple=False)

        relative_path = 'temporary_file'

        self.assertEqual([relative_path], result)

    def test_get_rel_path_to_source__source_file_in_child_directory(self):
        temp = '/c/users/folder/temporary_file'
        tag_file = '/c/users/tags'

        result = ctagsplugin.get_rel_path_to_source(
            temp, tag_file, multiple=False)

        # handle [windows, unix] paths
        relative_paths = ['folder\\temporary_file', 'folder/temporary_file']

        #self.assertEquals([relative_path], result)
        self.assertIn(result[0], relative_paths)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
