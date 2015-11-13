__FILENAME__ = compat

try:
    unicode_ = unicode
except NameError:
    # Python3
    unicode_ = str

try:
    basestring_ = basestring
except NameError:
    # Python3
    basestring_ = str


########NEW FILE########
__FILENAME__ = csvfdw
"""
A CSV Foreign Data Wrapper

"""


from . import ForeignDataWrapper
from .utils import log_to_postgres
from logging import WARNING
import csv


class CsvFdw(ForeignDataWrapper):
    """A foreign data wrapper for accessing csv files.

    Valid options:
        - filename : full path to the csv file, which must be readable
          by the user running postgresql (usually postgres)
        - delimiter : the delimiter used between fields.
          Default: ","
    """

    def __init__(self, fdw_options, fdw_columns):
        super(CsvFdw, self).__init__(fdw_options, fdw_columns)
        self.filename = fdw_options["filename"]
        self.delimiter = fdw_options.get("delimiter", ",")
        self.quotechar = fdw_options.get("quotechar", '"')
        self.skip_header = int(fdw_options.get('skip_header', 0))
        self.columns = fdw_columns

    def execute(self, quals, columns):
        with open(self.filename) as stream:
            reader = csv.reader(stream, delimiter=self.delimiter)
            count = 0
            checked = False
            for line in reader:
                if count >= self.skip_header:
                    if not checked:
                        # On first iteration, check if the lines are of the
                        # appropriate length
                        checked = True
                        if len(line) > len(self.columns):
                            log_to_postgres("There are more columns than "
                                            "defined in the table", WARNING)
                        if len(line) < len(self.columns):
                            log_to_postgres("There are less columns than "
                                            "defined in the table", WARNING)
                    yield line[:len(self.columns)]
                count += 1

########NEW FILE########
__FILENAME__ = docutils_meta
"""
Use low-level docutils API to extract metadata from ReStructuredText files.
"""

from collections import OrderedDict
from threading import Lock
from functools import wraps
from os.path import getmtime

from docutils.core import publish_doctree


def extract_meta(filename):
    """Read meta-data from a reStructuredText file and return a dict.

    The 'title' and 'subtitle' keys are special-cased, but other keys
    are read from the `docinfo` element.

    """
    with open(filename) as file_obj:
        content = file_obj.read()
    meta = {}
    for element in publish_doctree(content):
        if element.tagname in ('title', 'subtitle'):
            meta[element.tagname] = element.astext()
        elif element.tagname == 'docinfo':
            for field in element:
                if field.tagname == 'field':
                    name, body = field.children
                    meta[name.astext().lower()] = body.astext()
                else:
                    meta[field.tagname.lower()] = field.astext()
    return meta


def mtime_lru_cache(function, max_size=100):
    """File mtime-based least-recently-used cache.

    :param function:
        A function that takes a filename as its single parameter.
        The file should exist, and the function's return value should
        only depend on the contents of the file.

    Return a decorated function that caches at most the ``max_size`` value.
    Least recently used value are dropped first. Cached values are invalidated
    when the files's modification time changes.

    Inspired from functools.lru_cache, which only exists in Python 3.2+.

    """
    lock = Lock()  # OrderedDict isn't threadsafe
    cache = OrderedDict()  # ordered least recent to most recent

    @wraps(function)
    def wrapper(filename):
        mtime = getmtime(filename)
        with lock:
            if filename in cache:
                old_mtime, result = cache.pop(filename)
                if old_mtime == mtime:
                    # Move to the end
                    cache[filename] = old_mtime, result
                    return result
        result = function(filename)
        with lock:
            cache[filename] = mtime, result  # at the end
            if len(cache) > max_size:
                cache.popitem(last=False)
        return result
    return wrapper

########NEW FILE########
__FILENAME__ = structuredfs
"""

Handle nicely a set of files in a structured directory.

"""
import os
import sys
import io
import re
import errno
import string
import collections
import fcntl
from multicorn.compat import unicode_, basestring_

vformat = string.Formatter().vformat


try:
    str.isidentifier
except AttributeError:
    # Python 2
    # http://docs.python.org/py3k/reference/lexical_analysis.html#identifiers
    # the uppercase and lowercase letters A through Z, the underscore _
    # and, except for the first character, the digits 0 through 9.
    _IDENTIFIERS_RE = re.compile('^[a-zA-Z_][a-zA-Z_0-9]*$')

    def isidentifier(string):
        """
        Return whether the given string is a valid Python identifier.
        """
        return _IDENTIFIERS_RE.match(string) is not None
else:
    # Python 3
    def isidentifier(string):
        """
        Return whether the given string is a valid Python identifier.
        """
        return string.isidentifier()


def _tokenize_pattern(pattern):
    """
    Return an iterable of tokens from a string pattern.

    >>> list(_tokenize_pattern('{category}/{number}_{name}.txt'))
    [('property', 'category'),
     ('path separator', '/'),
     ('category', 'number'),
     ('literal', '_'),
     ('category', 'name'),
     ('path separator', '/')]

    """
    # We could re-purpose the parser for str.format() and use string.Formatter,
    # but we do not want to parse conversions and format specs.
    in_field = False
    field_name = None
    char_list = list(pattern)
    for prev_char, char, next_char in zip(
            [None] + char_list[:-1],
            char_list,
            char_list[1:] + [None]):
        if in_field:
            if char == '}':
                yield 'property', field_name
                field_name = None
                in_field = False
            else:
                field_name += char
        else:
            if char == '/':
                yield 'path separator', char
            elif char in '{}' and next_char == char:
                # Two brakets are parsed as one. Ignore the first one.
                pass
            elif char == '}' and prev_char != char:
                raise ValueError("Single '}' encountered in format string")
            elif char == '{' and prev_char != char:
                in_field = True
                field_name = ''
            else:
                # Includes normal chars but also an escaped bracket.
                yield 'literal', char
    if in_field:
        raise ValueError("Unmatched '{' in format string")

    # Artificially add this token to simplify the parser below
    yield 'path separator', '/'


def _parse_pattern(pattern):
    r"""
    Parse a string pattern and return (path_parts_re, path_parts_properties)

    >>> _parse_pattern('{category}/{number}_{name}.txt')
    (
        (
            <re object '^(?P<category>.*)$'>,
            <re object r'^(?P<number>.*)\_(?P<name>.*)\.txt$'>
        ), (
            ('category',)
            ('number', 'name')
        ),
    )
    """
    # A list of list of names
    path_parts_properties = []
    # The next list of names, being built
    properties = []
    # A set of all names
    all_properties = set()

    # A list of compiled re objects
    path_parts_re = []
    # The pattern being built for the next re
    next_re = ''

    for token_type, token in _tokenize_pattern(pattern):
        if token_type == 'path separator':
            if not next_re:
                raise ValueError('A slash-separated part is empty in %r' %
                                 pattern)
            path_parts_re.append(re.compile('^%s$' % next_re))
            next_re = ''
            path_parts_properties.append(tuple(properties))
            properties = []
        elif token_type == 'property':
            if not isidentifier(token):
                raise ValueError('Invalid property name for Filesystem: %r. '
                                 'Must be a valid identifier' % token)
            if token in all_properties:
                raise ValueError('Property name %r appears more than once '
                                 'in the pattern %r.' % (token, pattern))
            all_properties.add(token)
            properties.append(token)
            next_re += '(?P<%s>.*)' % token
        elif token_type == 'literal':
            next_re += re.escape(token)
        else:
            assert False, 'Unexpected token type: ' + token_type

    # Always end with an artificial '/' token so that the last regex is
    # in path_parts_re.
    assert token_type == 'path separator'

    return tuple(path_parts_re), tuple(path_parts_properties)


def strict_unicode(value):
    """
    Make sure that value is either unicode or (on Py 2.x) an ASCII string,
    and return it in unicode. Raise otherwise.
    """
    if not isinstance(value, basestring_):
        raise TypeError('Filename property values must be of type '
                        'unicode, got %r.' % value)
    return unicode_(value)


class Item(collections.Mapping):
    """
    Represents a single file in a :class:`StructuredDirectory`.

    Can be used as a mapping (dict-like) to access properties.

    Note that at a given point in time, the actual file for an Item may or
    may not exist in the filesystem.
    """
    def __init__(self, directory, properties, content=b''):
        properties = dict(properties)
        keys = set(properties)
        missing = directory.properties - keys
        if missing:
            raise ValueError('Missing properties: %s', ', '.join(missing))
        extra = keys - directory.properties
        if extra:
            raise ValueError('Unknown properties: %s', ', '.join(extra))
        self.directory = directory
        self._properties = {}
        self.content = content
        # TODO: check for ambiguities.
        # eg. with pattern = '{a}_{b}', values {'a': '1_2', 'b': '3'} and
        # {'a': '1', 'b': '2_3'} both give the same filename.
        for name, value in properties.items():
            value = strict_unicode(value)
            if '/' in value:
                raise ValueError('Property values can not contain a slash.')
            self._properties[name] = value

    @property
    def filename(self):
        """
        Return the normalized (slash-separated) filename for the item,
        relative to the root.
        """
        return vformat(self.directory.pattern, [], self)

    @property
    def full_filename(self):
        """
        Return the absolute filename for the item, in OS-specific form.
        """
        return self.directory._join(self.filename.split('/'))

    def open(self, shared_lock=True, fail_if=None):
        """Open the file underlying this item, if it is not in the cache.
        Shared_lock is a boolean indicating whether a shared or exclusive lock
        should be acquired.
        fail_if can be either None, "exists", or "missing".
        """
        self._fd, is_shared = self.directory.cache.get(self.full_filename,
                                                       (None, False))
        if shared_lock:
            if self._fd is None:
                # Open it with a shared lock
                self._fd = os.open(self.full_filename,
                                   os.O_RDONLY | os.O_SYNC)
                fcntl.flock(self._fd, fcntl.LOCK_SH)
                self.directory.cache[self.full_filename] = (self._fd,
                                                            shared_lock)
            # Do nothing if we already have a file descriptor
        else:
            if (self._fd is None or
                    not  (fcntl.fcntl(self._fd, fcntl.F_GETFL) & os.O_RDWR)):
                # Open it with an exclusive lock, sync mode, and fail if the
                # file already exists.
                dirname = os.path.dirname(self.full_filename)
                if not os.path.exists(dirname):
                    umask = os.umask(0)
                    os.makedirs(dirname, self.directory.file_mode)
                    os.umask(umask)
                flags = os.O_SYNC | os.O_RDWR
                if fail_if == 'exists':
                    flags = flags | os.O_CREAT | os.O_EXCL
                elif fail_if is None:
                    flags = flags | os.O_CREAT
                if self._fd is not None:
                    os.close(self._fd)

                umask = os.umask(0)
                self._fd = os.open(self.full_filename, flags,
                                   self.directory.file_mode)
                os.umask(umask)
            fcntl.flock(self._fd, fcntl.LOCK_EX)
            self.directory.cache[self.full_filename] = (self._fd, shared_lock)
        return self._fd

    def read(self):
        """
        Return the content of the file as a bytestring.

        :raises IOError: if the file does not exist in the filesystem.
        """
        fd = self.open(True, fail_if='missing')
        os.lseek(fd, 0, os.SEEK_SET)
        iof = io.open(fd, 'rb', closefd=False)
        content = iof.read()
        iof.close()
        return content

    def write(self, fd=None):
        if fd is None:
            fd = self.open(False)
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        # Do not use a buffer, to ensure that the file is written in one
        # syscall.
        iof = io.open(fd, 'wb', closefd=False,
                      buffering=0)

        if isinstance(self.content, unicode_):
            self.content = self.content.encode(sys.getfilesystemencoding())

        if self.content is not None:
            iof.write(self.content)
        iof.close()

    def remove(self):
        os.unlink(self.full_filename)

    # collections.Mapping interface:

    def __len__(self):
        return len(self._properties)

    def __iter__(self):
        return iter(self._properties)

    def __getitem__(self, name):
        return self._properties[name]

    def __setitem__(self, name, value):
        self._properties[name] = value


class StructuredDirectory(object):
    """
    :param root_dir: Path to the root directory
    :param pattern: Pattern for files in this directory,
                    eg. '{category}/{number}_{name}.txt'
    """
    def __init__(self, root_dir, pattern, file_mode=0o700):
        self.root_dir = unicode_(root_dir)
        self.pattern = unicode_(pattern)
        # Cache for file descriptors.
        self.cache = {}
        parts_re, parts_properties = _parse_pattern(self.pattern)
        self.file_mode = file_mode
        self._path_parts_re = parts_re
        self._path_parts_properties = parts_properties
        self.properties = set(prop for part in parts_properties
                              for prop in part)

    def create(self, **values):
        """
        Return a new ``Item`` associated to this directory with the given
        ``values``.

        The file for this item may or may not exist.

        """
        return Item(self, values)

    def from_filename(self, filename):
        """
        Return an ``Item`` from a slash-separated ``filename`` relative
        to the root. Return ``None`` if ``filename`` does not match
        ``pattern``.

        Assuming a matching filename::

            f = 'a/b/c'
            directory.from_filename(f).filename == f

        The file for this item may or may not exist.

        """
        values = {}
        parts = filename.split('/')
        if len(parts) != len(self._path_parts_re):
            return None
        for part, part_re in zip(parts, self._path_parts_re):
            match = part_re.match(part)
            if match is None:
                return None
            values.update(match.groupdict())
        return Item(self, values)

    def get_items(self, **fixed_values):
        """
        Return an iterable of :class:`Item` objects for all files
        that match the given ``properties``.
        """
        keys = set(fixed_values)
        extra = keys - self.properties
        if extra:
            raise ValueError('Unknown properties: %s', ', '.join(extra))

        # Pre-compute everything we know about the request without looking
        # at the filesystem.

        # `fixed` is a list, one element for each "part" of the pattern.
        # Each element is a (fixed_part, fixed_part_values) tuple.
        #    fixed_part: the whole part if it is completly fixed, or None
        #    fixed_part_values: (name, value) pairs for$ fixed values
        #                       for this part.
        fixed = []
        for pattern_part, part_properties in zip(
                self.pattern.split('/'), self._path_parts_properties):
            fixed_part_values = tuple(
                (name, fixed_values[name]) for name in part_properties
                if name in fixed_values
            )
            if len(fixed_part_values) == len(part_properties):
                # All properties for this part are fixed
                fixed_part = vformat(pattern_part, [], dict(fixed_part_values))
            else:
                fixed_part = None
            fixed.append((fixed_part, fixed_part_values))

        return self._walk((), (), fixed)

    def clear_cache_entry(self, key):
        value, shared = self.cache.pop(key)
        os.close(value)

    def clear_cache(self, only_shared=False):
        for key, (value, shared) in list(self.cache.items()):
            if (not only_shared) or shared:
                self.clear_cache_entry(key)

    def _walk(self, previous_path_parts, previous_values, fixed):
        """
        Called for each directory or sub-directory.
        """
        # Empty previous_path_parts means look in root_dir, depth = 0
        depth = len(previous_path_parts)
        # If the pattern has N path parts, "leaf" files are at depth = N-1
        is_leaf = (depth == len(self._path_parts_re) - 1)

        for name, part_values in self._find_matching_names(
                previous_path_parts, fixed):
            path_parts = previous_path_parts + (name,)
            values = previous_values + tuple(part_values)
            filename = self._join(path_parts)
            if is_leaf:
                if os.path.isfile(filename):
                    yield Item(self, values)
            # Do not check if filename is a directory or even exists,
            # let listdir() raise later.
            else:
                for item in self._walk(path_parts, values, fixed):
                    yield item

    def _find_matching_names(self, previous_path_parts, fixed):
        """
        Yield names and parsed values that match the request in a directory.
        """
        depth = len(previous_path_parts)
        fixed_part, fixed_part_values = fixed[depth]
        if fixed_part is not None:
            yield fixed_part, fixed_part_values
            return

        try:
            names = self._listdir(previous_path_parts)
        except OSError as exc:
            if depth > 0 and exc.errno in [errno.ENOENT, errno.ENOTDIR]:
                # Does not exist or is not a directory, just return
                # without yielding any name.
                # If depth == 0, we're listing the root directory. Still raise
                # in that case.
                return
            else:
                # Re-raise other errors
                raise
        for name in names:
            match = self._path_parts_re[depth].match(name)
            if match is None:
                continue

            part_values = match.groupdict()
            if all(part_values[name] == value
                   for name, value in fixed_part_values):
                yield name, list(part_values.items())

    def _join(self, path_parts):
        """
        Return a full filesystem path from parts relative to the root.
        """
        # root_dir is unicode, so the join result should be unicode
        return os.path.join(self.root_dir, *path_parts)

    def _listdir(self, path_parts):
        """
        Wrap os.listdir to make it monkey-patchable in tests.
        """
        return os.listdir(self._join(path_parts))

########NEW FILE########
__FILENAME__ = test
# coding: utf8

"""

Tests for StructuredFS.

"""


import os
import sys
import functools
import tempfile
import shutil
from contextlib import contextmanager
from multicorn.compat import unicode_
import pytest

from .structuredfs import StructuredDirectory, Item
from .docutils_meta import mtime_lru_cache, extract_meta


def with_tempdir(function):
    @functools.wraps(function)
    def wrapper():
        directory = tempfile.mkdtemp()
        try:
            return function(directory)
        finally:
            shutil.rmtree(directory)
    return wrapper


@contextmanager
def assert_raises(exception_class, message_part):
    """
    Check that an exception is raised and its message contains some string.
    """
    try:
        yield
    except exception_class as exception:
        assert message_part.lower() in exception.args[0].lower()
    else:
        assert 0, 'Did not raise %s' % exception_class


@with_tempdir
def test_parser(tempdir):
    """
    Test the pattern parser.
    """
    make = functools.partial(StructuredDirectory, tempdir)

    with assert_raises(ValueError, 'slash-separated part is empty'):
        assert make('')
    with assert_raises(ValueError, 'slash-separated part is empty'):
        assert make('/a')
    with assert_raises(ValueError, 'slash-separated part is empty'):
        assert make('a/')
    with assert_raises(ValueError, 'slash-separated part is empty'):
        assert make('a//b')
    with assert_raises(ValueError, 'more than once'):
        assert make('{foo}/{foo}')
    with assert_raises(ValueError, 'Invalid property name'):
        assert make('{}')
    with assert_raises(ValueError, 'Invalid property name'):
        assert make('{0foo}')
    with assert_raises(ValueError, 'Invalid property name'):
        assert make('{foo/bar}')
    with assert_raises(ValueError, 'Invalid property name'):
        assert make('{foo!r}')
    with assert_raises(ValueError, 'Invalid property name'):
        assert make('{foo:s}')
    with assert_raises(ValueError, "unmatched '{'"):
        assert make('foo{bar')
    with assert_raises(ValueError, "single '}'"):
        assert make('foo}bar')

    bin = make('{category}/{num}_{name}.bin')
    assert bin.properties == set(['category', 'num', 'name'])
    assert bin._path_parts_properties == (('category',), ('num', 'name'))

    bin = make('{category}/{{num}}_{name}.bin')
    assert bin.properties == set(['category', 'name'])
    assert bin._path_parts_properties == (('category',), ('name',))
    assert [regex.pattern for regex in bin._path_parts_re] \
        == ['^(?P<category>.*)$', r'^\{num\}\_(?P<name>.*)\.bin$']


@with_tempdir
def test_filenames(tempdir):
    binary = StructuredDirectory(tempdir, '{category}/{num}_{name}.bin')
    text = StructuredDirectory(tempdir, '{category}/{num}_{name}.txt')

    # No file created yet
    assert os.listdir(tempdir) == []

    # Create some files
    for path_parts in [
            # Matching the pattern
            ['lipsum', '4_foo.bin'],
            ['lipsum', '4_foo.txt'],

            # Not matching the pattern
            ['lipsum', '4_foo'],
            ['lipsum', '4-foo.txt'],
            ['lipsum', '4_bar.txt', 'baz'],
            ['lipsum', '4'],
            ['dolor']]:
        filename = os.path.join(tempdir, *path_parts)
        dirname = os.path.dirname(filename)
        # Create parent directories as needed
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        # Create an empty file
        open(filename, 'wb').close()

    assert [i.filename for i in text.get_items()] == ['lipsum/4_foo.txt']
    assert [i.filename for i in binary.get_items()] == ['lipsum/4_foo.bin']


@with_tempdir
def test_items(tempdir):
    """
    Test the :class:`Item` class.
    """
    binary = StructuredDirectory(tempdir, '{category}/{num}_{name}.bin')
    text = StructuredDirectory(tempdir, '{category}/{num}_{name}.txt')

    with assert_raises(ValueError, 'Missing properties'):
        text.create(category='lipsum')

    with assert_raises(ValueError, 'Unknown properties'):
        text.create(category='lipsum', num='4', name='foo', bang='bar')

    with assert_raises(TypeError, 'must be of type unicode'):
        text.create(category='lipsum', num=4, name='foo')

    with assert_raises(ValueError, 'can not contain a slash'):
        text.create(category='lipsum', num='4', name='foo/bar')

    values = dict(category='lipsum', num='4', name='foo')
    assert Item(binary, values).filename == 'lipsum/4_foo.bin'
    assert Item(text, values).filename == 'lipsum/4_foo.txt'

    # No file created yet
    assert os.listdir(tempdir) == []

    # Create a file directly
    os.mkdir(os.path.join(text.root_dir, 'lipsum'))
    open(os.path.join(text.root_dir, 'lipsum', '4_foo.txt'), 'wb').close()

    # Create a file from an Item
    text.create(category='lipsum', num='5', name='bar').write('BAR')

    item_foo, item_bar, = sorted(text.get_items(),
                                 key=lambda item: item['num'])
    assert len(item_foo) == 3
    assert dict(item_foo) == dict(category='lipsum', num='4', name='foo')
    assert item_foo.read() == ''

    assert len(item_bar) == 3
    assert dict(item_bar) == dict(category='lipsum', num='5', name='bar')
    assert item_bar.read() == 'BAR'

    content = b'Hello,\xc2\xa0W\xc3\xb6rld!'.decode('utf-8')
    with pytest.raises(UnicodeError):
        item_foo.write(content)
    item_foo.write(content.encode('utf8'))
    assert item_foo.read().decode('utf8') == content
    item_foo.remove()
    with pytest.raises(IOError):
        item_foo.read()
    with pytest.raises(OSError):
        item_foo.remove()

    assert [i.filename for i in text.get_items()] == ['lipsum/5_bar.txt']
    item_bar.remove()
    assert [i.filename for i in text.get_items()] == []
    # The 'lipsum' directory was also removed
    assert os.listdir(tempdir) == []


@with_tempdir
def test_get_items(tempdir):
    """
    Test the results of :meth:`StructuredDirectory.get_items`
    """
    text = StructuredDirectory(tempdir, '{category}/{num}_{name}.txt')

    text.create(category='lipsum', num='4', name='foo').write('FOO')
    text.create(category='lipsum', num='5', name='bar').write('BAR')

    def filenames(**properties):
        return [i.filename for i in text.get_items(**properties)]

    assert filenames(num='9') == []
    assert filenames(num='5', name='UUU') == []
    assert filenames(num='5') == ['lipsum/5_bar.txt']
    assert filenames(num='5', name='bar') == ['lipsum/5_bar.txt']
    assert sorted(filenames()) == ['lipsum/4_foo.txt', 'lipsum/5_bar.txt']

    with assert_raises(ValueError, 'Unknown properties'):
        filenames(fiz='5')


@with_tempdir
def test_from_filename(tempdir):
    """
    Test the results of :meth:`StructuredDirectory.from_filename`
    """
    text = StructuredDirectory(tempdir, '{category}/{num}_{name}.txt')

    assert text.from_filename('lipsum/4_foo.txt/bar') is None
    assert text.from_filename('lipsum') is None
    assert text.from_filename('lipsum/4') is None
    assert text.from_filename('lipsum/4_foo.bin') is None
    matching = text.from_filename('lipsum/4_foo.txt')
    assert dict(matching) == dict(category='lipsum', num='4', name='foo')
    assert matching.filename == 'lipsum/4_foo.txt'


@with_tempdir
def test_optimizations(tempdir):
    """
    Test that :meth:`StructuredDirectory.get_items` doesn’t do more calls
    to :func:`os.listdir` than needed.
    """
    text = StructuredDirectory(tempdir, '{cat}/{org}_{name}/{id}')

    listed = []
    real_listdir = text._listdir

    def listdir_mock(parts):
        listed.append('/'.join(parts))
        return real_listdir(parts)

    text._listdir = listdir_mock

    contents = {}

    def create(**values):
        item = Item(text, values)
        assert values['id'] not in contents  # Make sure ids are unique
        content = item.filename.encode('ascii')
        item.write(content)
        contents[values['id']] = content

    def assert_listed(properties, expected_ids, expected_listed):
        del listed[:]
        expected_contents = set(contents[num] for num in expected_ids)
        results = [item.read() for item in text.get_items(**properties)]
        assert set(results) == expected_contents
        assert set(listed) == set(expected_listed)

    create(cat='lipsum', org='a', name='foo', id='1')

    # No fixed values: all directories on the path are listed.
    assert_listed(dict(),
        ['1'],
        ['', 'lipsum', 'lipsum/a_foo'])

    # The category was fixed, no need to listdir() the root.
    assert_listed(dict(cat='lipsum'),
        ['1'],
        ['lipsum', 'lipsum/a_foo'])

    # The num and name were fixed, no need to listdir() the lipsum dir.
    assert_listed(dict(org='a', name='foo'),
        ['1'],
        ['', 'lipsum/a_foo'])

    # All filename properties were fixed, no need to listdir() anything
    assert_listed(dict(cat='lipsum', org='a', name='foo', id='1'),
        ['1'],
        [])

    create(cat='lipsum', org='b', name='foo', id='2')
    create(cat='dolor', org='c', name='bar', id='3')

    assert_listed(dict(),
        ['1', '2', '3'],
        ['', 'lipsum', 'dolor', 'lipsum/a_foo', 'lipsum/b_foo', 'dolor/c_bar'])

    # No need to listdir() the root
    assert_listed(dict(cat='lipsum'),
        ['1', '2'],
        ['lipsum', 'lipsum/a_foo', 'lipsum/b_foo'])

    # No need to listdir() the root
    assert_listed(dict(cat='dolor'),
        ['3'],
        ['dolor', 'dolor/c_bar'])

    # org='b' is not a whole part so we still need to listdir() lipsum,
    # but can filter out some deeper directories
    assert_listed(dict(org='b'),
        ['2'],
        ['', 'lipsum', 'dolor', 'lipsum/b_foo'])

    # Does not list the root and directry tries to list 'nonexistent'
    assert_listed(dict(cat='nonexistent'),
        [],
        ['nonexistent'])


@with_tempdir
def test_docutils_meta(tempdir):
    def counting(filename):
        counting.n_calls += 1
        return extract_meta(filename)
    counting.n_calls = 0
    wrapper = mtime_lru_cache(counting, max_size=2)
    def extract(filename):
        return wrapper(os.path.join(tempdir, filename))
    rest_1 = '''
The main title
==============

Second title
------------

:Author: Me

Content
'''
    meta_1 = {'title': 'The main title', 'subtitle': 'Second title',
              'author': 'Me'}
    rest_2 = '''
First title
===========

:Author: Myself
:Summary:
    Lorem ipsum
    dolor sit amet

Not a subtitle
--------------

Content
'''
    meta_2 = {'title': 'First title', 'author': 'Myself',
              'summary': 'Lorem ipsum\ndolor sit amet'}
    def write(filename, content):
        with open(os.path.join(tempdir, filename), 'w') as file_obj:
            file_obj.write(content)
    write('first.rst', rest_1)
    write('second.rst', rest_2)
    assert counting.n_calls == 0
    assert extract('first.rst') == meta_1
    assert counting.n_calls == 1
    assert extract('first.rst') == meta_1  # cached
    assert counting.n_calls == 1
    assert extract('second.rst') == meta_2
    assert counting.n_calls == 2
    write('third.rst', rest_1)
    assert extract('third.rst') == meta_1  # Exceeds the cache size
    assert counting.n_calls == 3
    write('third.rst', rest_2)
    assert extract('third.rst') == meta_2
    assert counting.n_calls == 4
    assert extract('first.rst') == meta_1  # Not cached anymore
    assert counting.n_calls == 5


if __name__ == '__main__':
    pytest.main([__file__] + sys.argv)

########NEW FILE########
__FILENAME__ = gcfdw
from multicorn import ForeignDataWrapper
import gc
import sys
import random
from multicorn.compat import unicode_, basestring_


class MyClass(object):

    def __init__(self, num, rand):
        self.num = num
        self.rand = rand

class GCForeignDataWrapper(ForeignDataWrapper):

    def execute(self, quals, columns):
        gc.collect()
        result = []
        for obj in gc.get_objects():
            tobj = type(obj)
            if isinstance(obj, bytes):
                obj = obj.decode('utf8')
            elif isinstance(obj, unicode_):
                pass
            else:
                try:
                    obj = bytes(obj).decode('utf8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    try:
                        obj = unicode_(obj)
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        obj = unicode_("<NA>")
            result.append({'object': obj,
                   'type': unicode_(tobj),
                   'id': unicode_(id(obj)),
                   'refcount': unicode_(sys.getrefcount(obj))})
        return result

class MemStressFDW(ForeignDataWrapper):

    def __init__(self, options, columns):
        self.nb = int(options.get('nb', 100000))
        self.options = options
        self.columns = columns
        super(MemStressFDW, self).__init__(options, columns)

    def execute(self, quals, columns):
        for i in range(self.nb):
            num = i / 100.
            yield {'value': str(MyClass(i, num)),
                           'i': i,
                           'num': num}

########NEW FILE########
__FILENAME__ = gitfdw
"""
A Git foreign data wrapper

"""

from . import ForeignDataWrapper
import brigit


class GitFdw(ForeignDataWrapper):
    """A Git foreign data wrapper.

    The git foreign data wrapper accepts the following options:

    path        --  the absolute path to the git repo. It must be readable by
                    the user running postgresql (usually, postgres).
    encoding    --  the file encoding. Defaults to "utf-8".

    """

    def __init__(self, fdw_options, fdw_columns):
        super(GitFdw, self).__init__(fdw_options, fdw_columns)
        self.path = fdw_options["path"]
        self.encoding = fdw_options.get("encoding", "utf-8")

    def execute(self, quals, columns):
        def enc(unicode_str):
            """Encode the string in the self given encoding."""
            return unicode_str.encode(self.encoding)
        for log in  brigit.Git(self.path).pretty_log():
            yield {
                'author_name': enc(log["author"]['name']),
                'author_email': enc(log["author"]['email']),
                'message': enc(log['message']),
                'hash': enc(log['hash']),
                'date': log['datetime'].isoformat()
            }

########NEW FILE########
__FILENAME__ = googlefdw
"""
A foreign data wrapper for performing google searches.

"""

from . import ForeignDataWrapper

import json
import urllib


def google(search):
    """Retrieves results from google using the json api"""
    query = urllib.urlencode({'q': search})
    url = ('http://ajax.googleapis.com/ajax/'
           'services/search/web?v=1.0&%s' % query)
    response = urllib.urlopen(url)
    results = response.read()
    results = json.loads(results)
    data = results['responseData']
    hits = data['results']
    for hit in hits:
        yield {'url': hit['url'].encode("utf-8"),
               'title': hit["titleNoFormatting"].encode("utf-8"),
               'search': search.encode("utf-8")}


class GoogleFdw(ForeignDataWrapper):
    """A Google search foreign data wrapper.

    Parses the quals to find anything ressembling a search criteria, and
    returns the google search result for it.
    Available columns are: url, title, search.

    """

    def execute(self, quals, columns):
        if not quals:
            return ("No search specified",)
        for qual in quals:
            if qual.field_name == "search" or qual.operator == "=":
                return google(qual.value)

########NEW FILE########
__FILENAME__ = imapfdw
from . import ForeignDataWrapper, ANY, ALL
from .utils import log_to_postgres, ERROR, WARNING

from imaplib import IMAP4

import re
from multicorn.compat import basestring_
from email.header import decode_header

from imapclient import IMAPClient
from itertools import islice

try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest

from functools import reduce


STANDARD_FLAGS = {
        'seen': 'Seen',
        'flagged': 'Flagged',
        'delete': 'Deleted',
        'draft': 'Draft',
        'recent': 'Recent'
}

SEARCH_HEADERS = ['BCC', 'CC', 'FROM', 'TO']


def compact_fetch(messages):
    """Compact result in ranges.

    For example, [1, 2, 3, 4, 10, 11, 12, 14, 17, 18, 19, 21, 92]
    can be compacted in ['1:4', '10:12', '14', '17:19', '21', '92']

    """
    first_i = messages[0]
    for (i, inext) in zip_longest(messages, islice(messages, 1, None)):
        if inext == i + 1:
            continue
        elif first_i != i:
            yield '%s:%s' % (first_i, i)
            first_i = inext
        else:
            yield "%s" % i
            first_i = inext


class NoMatchPossible(Exception):
    """An exception raised when the conditions can NOT be met by any message,
    ever."""


def make_or(values):
    """Create an imap OR filter based on a list of conditions to be or'ed"""
    values = [x for x in values if x not in (None, '()')]
    if values:
        if len(values) > 1:
            return reduce(lambda x, y: '(OR %s %s)' % (x, y), values)
        else:
            return values[0]


class ImapFdw(ForeignDataWrapper):
    """An imap foreign data wrapper
    """

    def __init__(self, options, columns):
        super(ImapFdw, self).__init__(options, columns)
        self._imap_agent = None
        self.host = options.get('host', None)
        if self.host is None:
            log_to_postgres('You MUST set the imap host',
            ERROR)
        self.port = options.get('port', None)
        self.ssl = options.get('ssl', False)
        self.login = options.get('login', None)
        self.password = options.get('password', None)
        self.folder = options.get('folder', 'INBOX')
        self.imap_server_charset = options.get('imap_server_charset', 'UTF8')
        self.columns = columns
        self.payload_column = options.get('payload_column', None)
        self.flags_column = options.get('flags_column', None)
        self.internaldate_column = options.get('internaldate_column', None)

    def get_rel_size(self, quals, columns):
        """Inform the planner that it can be EXTREMELY costly to use the
        payload column, and that a query on Message-ID will return only one row."""
        width = len(columns) * 100
        nb_rows = 1000000
        if self.payload_column in columns:
            width += 100000000000
        nb_rows = nb_rows / (10 ** len(quals))
        for qual in quals:
            if qual.field_name.lower() == 'in-reply-to' and\
                    qual.operator == '=':
                nb_rows = 10
            if qual.field_name.lower() == 'message-id' and qual.operator == '=':
                nb_rows = 1
                break
        return (nb_rows, width)

    def _create_agent(self):
        self._imap_agent = IMAPClient(self.host, self.port, ssl=self.ssl)
        if self.login:
            self._imap_agent.login(self.login, self.password)
        self._imap_agent.select_folder(self.folder)

    @property
    def imap_agent(self):
        if self._imap_agent is None:
            self._create_agent()
        try:
            self._imap_agent.select_folder(self.folder)
        except IMAP4.abort:
            self._create_agent()
        return self._imap_agent

    def get_path_keys(self):
        """Helps the planner by supplying a list of list of access keys, as well
        as a row estimate for each one."""
        return [(('Message-ID',), 1), (('From',), 100), (('To',), 100),
                (('In-Reply-To',), 10)]

    def _make_condition(self, key, operator, value):
        if operator not in ('~~', '!~~', '=', '<>', '@>', '&&', '~~*', '!~~*'):
            # Do not manage special operators
            return ''
        if operator in ('~~', '!~~', '~~*', '!~~*') and\
                isinstance(value, basestring_):
            # 'Normalize' the sql like wildcards
            if value.startswith(('%', '_')):
                value = value[1:]
            if value.endswith(('%', '_')):
                value = value[:-1]
            if re.match(r'.*[^\\][_%]', value):
                return ''
            value = value.replace('\\%', '%').replace('\\_', '_')
        prefix = ''
        if operator in ('!~~', '<>', '!~~*'):
            if key == self.flags_column:
                prefix = 'UN'
            else:
                prefix = 'NOT '
            if isinstance(value, basestring_):
                if value.lower() in STANDARD_FLAGS:
                    prefix = ''
                    value = value.upper()
        if key == self.flags_column:
            if operator == '@>':
                # Contains on flags
                return ' '.join(['%s%s' % (prefix,
                    (STANDARD_FLAGS.get(atom.lower(), '%s %s'
                    % ('KEYWORD', atom))))  for atom in value])
            elif operator == '&&':
                # Overlaps on flags => Or
                values = ['(%s%s)' %
                    (prefix, (STANDARD_FLAGS.get(atom.lower(), '%s %s' %
                    ('KEYWORD', atom))))  for atom in value]
                return make_or(values)
            else:
                value = '\\\\%s' % value
        elif key == self.payload_column:
            value = 'TEXT "%s"' % value
        elif key in SEARCH_HEADERS:
            value = '%s "%s"' % (key, value)
        else:
            # Special case for Message-ID and In-Reply-To:
            # zero-length strings are forbidden so dont bother
            # searching them
            if not value:
                raise NoMatchPossible()
            prefix = 'HEADER '
            value = '%s "%s"' % (key, value)
        return '%s%s' % (prefix, value)

    def extract_conditions(self, quals):
        """Build an imap search criteria string from a list of quals"""
        conditions = []
        for qual in quals:
            # Its a list, so we must translate ANY to OR, and ALL to AND
            if qual.list_any_or_all == ANY:
                values = [
                    '(%s)' % self._make_condition(qual.field_name,
                        qual.operator[0], value)
                    for value in qual.value]
                conditions.append(make_or(values))
            elif qual.list_any_or_all == ALL:
                conditions.extend([
                    self._make_condition(qual.field_name, qual.operator[0],
                        value)
                    for value in qual.value])
            else:
                # its not a list, so everything is fine
                conditions.append(self._make_condition(qual.field_name,
                    qual.operator, qual.value))
        conditions = [x for x in conditions if x not in (None, '()')]
        return conditions

    def execute(self, quals, columns):
        # The header dictionary maps columns to their imap search string
        col_to_imap = {}
        headers = []
        for column in list(columns):
            if column == self.payload_column:
                col_to_imap[column] = 'BODY[TEXT]'
            elif column == self.flags_column:
                col_to_imap[column] = 'FLAGS'
            elif column == self.internaldate_column:
                col_to_imap[column] = 'INTERNALDATE'
            else:
                col_to_imap[column] = 'BODY[HEADER.FIELDS (%s)]' %\
                        column.upper()
                headers.append(column)
        try:
            conditions = self.extract_conditions(quals) or ['ALL']
        except NoMatchPossible:
            matching_mails = []
        else:
            matching_mails = self.imap_agent.search(
                charset=self.imap_server_charset,
                criteria=conditions)
        if matching_mails:
            data = self.imap_agent.fetch(list(compact_fetch(matching_mails)),
                                         list(col_to_imap.values()))
            item = {}
            for msg in data.values():
                for column, key in col_to_imap.items():
                    item[column] = msg[key]
                    if column in headers:
                        item[column] = item[column].split(':', 1)[-1].strip()
                        values = decode_header(item[column])
                        for decoded_header, charset in values:
                            # Values are of the from "Header: value"
                            if charset:
                                try:
                                    item[column] = decoded_header.decode(
                                            charset)
                                except LookupError:
                                    log_to_postgres('Unknown encoding: %s' %
                                            charset, WARNING)
                            else:
                                item[column] = decoded_header
                yield item

########NEW FILE########
__FILENAME__ = ldapfdw
"""
An LDAP foreign data wrapper.

"""

from . import ForeignDataWrapper

import ldap
from multicorn.utils import log_to_postgres, ERROR
from multicorn.compat import unicode_


SPECIAL_CHARS = {
    ord('*'): '\\2a',
    ord('('): '\\28',
    ord(')'): '\29',
    ord('\\'): '\\5c',
    ord('\x00'): '\\00',
    ord('/'): '\\2f'
}


class LdapFdw(ForeignDataWrapper):
    """An Ldap Foreign Wrapper.

    The following options are required:

    uri                -- the ldap URI to connect. (ex: 'ldap://localhost')
    address     -- the ldap host to connect. (obsolete)
    path        -- the ldap path (ex: ou=People,dc=example,dc=com)
    objectClass -- the ldap object class (ex: 'inetOrgPerson')
    scope        -- the ldap scope (one, sub or base)
    binddn        -- the ldap bind DN (ex: 'cn=Admin,dc=example,dc=com')
    bindpwd        -- the ldap bind Password

    """

    def __init__(self, fdw_options, fdw_columns):
        super(LdapFdw, self).__init__(fdw_options, fdw_columns)
        if "address" in fdw_options:
            self.ldapuri = "ldap://" + fdw_options["address"]
        else:
            self.ldapuri = fdw_options["uri"]
        self.ldap = ldap.initialize(self.ldapuri)
        self.path = fdw_options["path"]
        self.scope = self.parse_scope(fdw_options.get("scope", None))
        self.object_class = fdw_options["objectclass"]
        self.field_list = fdw_columns
        self.field_definitions = dict((name.lower(), field)
                                      for name, field
                                      in self.field_list.items())
        self.binddn = fdw_options.get("binddn", None)
        self.bindpwd = fdw_options.get("bindpwd", None)
        self.array_columns = [col.column_name for name, col
                              in self.field_definitions.items()
                              if col.type_name.endswith('[]')]
        self.bind()

    def execute(self, quals, columns):
        request = unicode_("(objectClass=%s)") % self.object_class
        for qual in quals:
            if isinstance(qual.operator, tuple):
                operator = qual.operator[0]
            else:
                operator = qual.operator
            if operator in ("=", "~~"):
                baseval = qual.value.translate(SPECIAL_CHARS)
                val = (baseval.replace("%", "*")
                       if operator == "~~" else baseval)
                request = unicode_("(&%s(%s=%s))") % (
                    request, qual.field_name, val)
        request = request.encode('utf8')
        for _, item in self.ldap.search_s(self.path, self.scope, request):
            # Case insensitive lookup for the attributes
            litem = dict()
            for key, value in item.items():
                if key.lower() in self.field_definitions:
                    pgcolname = self.field_definitions[key.lower()].column_name
                    if pgcolname in self.array_columns:
                        value = value
                    else:
                        value = value[0]
                    litem[pgcolname] = value
            yield litem

    def bind(self):
        try:
            args = {}
            if self.binddn is not None:
                args['who'] = self.binddn
                if self.bindpwd is not None:
                    args['cred'] = self.bindpwd
            self.ldap.simple_bind_s(**args)

        except ldap.INVALID_CREDENTIALS as msg:
            log_to_postgres("LDAP BIND Error: %s" % msg, ERROR)
        except ldap.UNWILLING_TO_PERFORM as msg:
            log_to_postgres("LDAP BIND Error: %s" % msg, ERROR)

    def parse_scope(self, scope=None):
        if scope in (None, "", "one"):
            return ldap.SCOPE_ONELEVEL
        elif scope == "sub":
            return ldap.SCOPE_SUBTREE
        elif scope == "base":
            return ldap.SCOPE_BASE
        else:
            log_to_postgres("Invalid scope specified: %s" % scope, ERROR)

########NEW FILE########
__FILENAME__ = processfdw
"""A process FDW"""

from . import ForeignDataWrapper
import statgrab


class ProcessFdw(ForeignDataWrapper):
    """A foreign datawrapper for querying system stats.

    It accepts no options.
    You can define any column named after a statgrab column.
    See the statgrab documentation.

    """

    def execute(self, quals, columns):
        # statgrab already returns its data in a format suitable
        # for Multicorn: a list (iterable) of dicts.
        # `quals` is ignored, PostgreSQL will do the filtering itself.
        return statgrab.sg_get_process_stats()

########NEW FILE########
__FILENAME__ = rssfdw
"""An RSS foreign data wrapper"""

from . import ForeignDataWrapper
from datetime import datetime, timedelta
from lxml import etree
try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen
from logging import ERROR
from multicorn.utils import log_to_postgres
import json


def element_to_dict(element):
    """
    This method takes a lxml element and return a json string containing
    the element attributes and a text key and a child node.
    >>> test = lambda x: sorted([(k, sorted(v.items())) if isinstance(v, dict) else (k, [sorted(e.items()) for e in v]) if isinstance(v, list) else (k, v) for k, v in element_to_dict(etree.fromstring(x)).items()])
    >>> test('<t a1="v1"/>')
    [('attributes', {'a1': 'v1'}), ('children', []), ('tag', 't'), ('text', '')]

    >>> test('<t a1="v1">Txt</t>')
    [('attributes', {'a1': 'v1'}), ('children', []), ('tag', 't'), ('text', 'Txt')]

    >>> test('<t>Txt<s1 a1="v1">Sub1</s1>Txt2<s2 a2="v2">Sub2</s2>Txt3</t>')
    [('attributes', {}), ('children', [[('attributes', {'a1': 'v1'}), ('children', []), ('tag', 's1'), ('text', 'Sub1')], [('attributes', {'a2': 'v2'}), ('children', []), ('tag', 's2'), ('text', 'Sub2')]]), ('tag', 't'), ('text', 'Txt')]

"""
    return {
        'tag': etree.QName(element.tag).localname,
        'text': element.text or '',
        'attributes': dict(element.attrib),
        'children': [element_to_dict(e) for e in element]
    }


class RssFdw(ForeignDataWrapper):
    """An rss foreign data wrapper.

    The following options are accepted:

    url --  The rss feed urls.

    The columns named are parsed, and are used as xpath expression on
    each item xml node. Exemple: a column named "pubDate" would return the
    pubDate element of an rss item.

    """

    def __init__(self, options, columns):
        super(RssFdw, self).__init__(options, columns)
        self.url = options.get('url', None)
        self.cache = (None, None)
        self.cache_duration = options.get('cache_duration', None)
        if self.cache_duration is not None:
            self.cache_duration = timedelta(seconds=int(self.cache_duration))
        if self.url is None:
            log_to_postgres("You MUST set an url when creating the table!",
                            ERROR)
        self.columns = columns

    def make_item_from_xml(self, xml_elem, namespaces):
        """Internal method used for parsing item xml element from the
        columns definition."""
        item = {}
        for prop, column in self.columns.items():
            value = xml_elem.xpath(prop, namespaces=namespaces)
            if value:
                if column.type_name.startswith('json'):
                    item[prop] = json.dumps([element_to_dict(val) for val in value])
                # There should be a better way
                # oid is 1009 ?
                elif column.type_name.endswith('[]'):
                    item[prop] = [elem.text for elem in value]
                else:
                    item[prop] = value[0].text
        return item

    def execute(self, quals, columns):
        """Quals are ignored."""
        if self.cache_duration is not None:
            date, values = self.cache
            if values is not None:
                if (datetime.now() - date) < self.cache_duration:
                    return values
        try:
            xml = etree.fromstring(urlopen(self.url).read())
            items = [self.make_item_from_xml(elem, xml.nsmap)
                     for elem in xml.xpath('//item')]
            self.cache = (datetime.now(), items)
            return items
        except etree.ParseError:
            log_to_postgres("Malformed xml, returning nothing")
            return

########NEW FILE########
__FILENAME__ = sqlalchemyfdw
"""A SQLAlchemy foreign data wrapper"""

from . import ForeignDataWrapper
from .utils import log_to_postgres, ERROR, WARNING, DEBUG
from sqlalchemy import create_engine
from sqlalchemy.sql import select, operators as sqlops, and_
# Handle the sqlalchemy 0.8 / 0.9 changes
try:
    from sqlalchemy.sql import sqltypes
except ImportError:
    from sqlalchemy import types as sqltypes

from sqlalchemy.schema import Table, Column, MetaData
from sqlalchemy.dialects.postgresql.base import ARRAY, ischema_names
import re
import operator


def compose(*funs):
    if len(funs) == 0:
        raise ValueError("At least one function is necessary for compose")
    if len(funs) == 1:
        return funs[0]
    else:
        result_fun = compose(*funs[1:])
        return lambda *args, **kwargs: funs[0](result_fun(*args, **kwargs))


def not_(function):
    return compose(operator.inv, function)


OPERATORS = {
    '=': operator.eq,
    '<': operator.lt,
    '>': operator.gt,
    '<=': operator.le,
    '>=': operator.ge,
    '<>': operator.ne,
    '~~': sqlops.like_op,
    '~~*': sqlops.ilike_op,
    '!~~*': not_(sqlops.ilike_op),
    '!~~': not_(sqlops.like_op),
    ('=', True): sqlops.in_op,
    ('<>', False): not_(sqlops.in_op)
}


class SqlAlchemyFdw(ForeignDataWrapper):
    """An SqlAlchemy foreign data wrapper.

    The sqlalchemy foreign data wrapper performs simple selects on a remote
    database using the sqlalchemy framework.

    Accepted options:

    db_url      --  the sqlalchemy connection string.
    schema      --  (optional) schema name to qualify table name with
    tablename   --  the table name in the remote database.

    """

    def __init__(self, fdw_options, fdw_columns):
        super(SqlAlchemyFdw, self).__init__(fdw_options, fdw_columns)
        if 'db_url' not in fdw_options:
            log_to_postgres('The db_url parameter is required', ERROR)
        if 'tablename' not in fdw_options:
            log_to_postgres('The tablename parameter is required', ERROR)
        self.engine = create_engine(fdw_options.get('db_url'))
        self.metadata = MetaData()
        schema = fdw_options['schema'] if 'schema' in fdw_options else None
        tablename = fdw_options['tablename']
        sqlacols = []
        for col in fdw_columns.values():
            col_type = self._get_column_type(col.type_name)
            sqlacols.append(Column(col.column_name, col_type))
        self.table = Table(tablename, self.metadata, schema=schema,
                           *sqlacols)
        self.transaction = None
        self._connection = None
        self._row_id_column = fdw_options.get('primary_key', None)

    def execute(self, quals, columns):
        """
        The quals are turned into an and'ed where clause.
        """
        statement = select([self.table])
        clauses = []
        for qual in quals:
            operator = OPERATORS.get(qual.operator, None)
            if operator:
                clauses.append(operator(self.table.c[qual.field_name],
                                        qual.value))
            else:
                log_to_postgres('Qual not pushed to foreign db: %s' % qual,
                                WARNING)
        if clauses:
            statement = statement.where(and_(*clauses))
        if columns:
            columns = [self.table.c[col] for col in columns]
        else:
            columns = self.table.c.values()
        statement = statement.with_only_columns(columns)
        log_to_postgres(str(statement), DEBUG)
        for item in self.connection.execute(statement):
            yield dict(item)

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self.engine.connect()
        return self._connection

    def begin(self, serializable):
        self.transaction = self.connection.begin()

    def pre_commit(self):
        if self.transaction is not None:
            self.transaction.commit()
            self.transaction = None

    def commit(self):
        # Pre-commit hook does this on 9.3
        if self.transaction is not None:
            self.transaction.commit()
            self.transaction = None

    def rollback(self):
        if self.transaction is not None:
            self.transaction.rollback()
            self.transaction = None

    @property
    def rowid_column(self):
        if self._row_id_column is None:
            log_to_postgres(
                'You need to declare a primary key option in order '
                'to use the write features')
        return self._row_id_column

    def insert(self, values):
        self.connection.execute(self.table.insert(values=values))

    def update(self, rowid, newvalues):
        self.connection.execute(
            self.table.update()
            .where(self.table.c[self._row_id_column] == rowid)
            .values(newvalues))

    def delete(self, rowid):
        self.connection.execute(
            self.table.delete()
            .where(self.table.c[self._row_id_column] == rowid))

    def _get_column_type(self, format_type):
        """Blatant ripoff from PG_Dialect.get_column_info"""
        ## strip (*) from character varying(5), timestamp(5)
        # with time zone, geometry(POLYGON), etc.
        attype = re.sub(r'\(.*\)', '', format_type)

        # strip '[]' from integer[], etc.
        attype = re.sub(r'\[\]', '', attype)

        is_array = format_type.endswith('[]')
        charlen = re.search('\(([\d,]+)\)', format_type)
        if charlen:
            charlen = charlen.group(1)
        args = re.search('\((.*)\)', format_type)
        if args and args.group(1):
            args = tuple(re.split('\s*,\s*', args.group(1)))
        else:
            args = ()
        kwargs = {}

        if attype == 'numeric':
            if charlen:
                prec, scale = charlen.split(',')
                args = (int(prec), int(scale))
            else:
                args = ()
        elif attype == 'double precision':
            args = (53, )
        elif attype == 'integer':
            args = ()
        elif attype in ('timestamp with time zone',
                        'time with time zone'):
            kwargs['timezone'] = True
            if charlen:
                kwargs['precision'] = int(charlen)
            args = ()
        elif attype in ('timestamp without time zone',
                        'time without time zone', 'time'):
            kwargs['timezone'] = False
            if charlen:
                kwargs['precision'] = int(charlen)
            args = ()
        elif attype == 'bit varying':
            kwargs['varying'] = True
            if charlen:
                args = (int(charlen),)
            else:
                args = ()
        elif attype in ('interval', 'interval year to month',
                        'interval day to second'):
            if charlen:
                kwargs['precision'] = int(charlen)
            args = ()
        elif charlen:
            args = (int(charlen),)

        coltype = ischema_names.get(attype, None)
        if coltype:
            coltype = coltype(*args, **kwargs)
            if is_array:
                coltype = ARRAY(coltype)
        else:
            coltype = sqltypes.NULLTYPE
        return coltype

########NEW FILE########
__FILENAME__ = statefdw
"""A dummy foreign data wrapper"""


from . import ForeignDataWrapper
from .utils import log_to_postgres
from logging import ERROR, DEBUG, INFO, WARNING


class StateFdw(ForeignDataWrapper):
    """A dummy foreign data wrapper.

    This dummy foreign data wrapper is intended as a proof of concept of state
    keeping foreign data wrappers.

    It keeps an internal state as an integer, auto-incremented at each request.
    """

    def __init__(self, *args):
        super(StateFdw, self).__init__(*args)
        self.state = 0

    def execute(self, quals, columns):
        self.state += 1
        yield [self.state]

########NEW FILE########
__FILENAME__ = testfdw
# -*- coding: utf-8 -*-
from multicorn import ForeignDataWrapper
from multicorn.compat import unicode_
from .utils import log_to_postgres, WARNING, ERROR
from itertools import cycle
from datetime import datetime


class TestForeignDataWrapper(ForeignDataWrapper):

    _startup_cost = 10

    def __init__(self, options, columns):
        super(TestForeignDataWrapper, self).__init__(options, columns)
        self.columns = columns
        self.test_type = options.get('test_type', None)
        self.tx_hook = options.get('tx_hook', False)
        self._row_id_column = options.get('row_id_column',
                                          list(self.columns.keys())[0])
        log_to_postgres(str(sorted(options.items())))
        log_to_postgres(str(sorted([(key, column.type_name) for key, column in
                                    columns.items()])))
        for column in columns.values():
            if column.options:
                log_to_postgres('Column %s options: %s' %
                                (column.column_name, column.options))
        if self.test_type == 'logger':
            log_to_postgres("An error is about to occur", WARNING)
            log_to_postgres("An error occured", ERROR)

    def _as_generator(self, quals, columns):
        random_thing = cycle([1, 2, 3])
        for index in range(20):
            if self.test_type == 'sequence':
                line = []
                for column_name in self.columns:
                    line.append('%s %s %s' % (column_name,
                                              next(random_thing), index))
            else:
                line = {}
                for column_name, column in self.columns.items():
                    if self.test_type == 'list':
                        line[column_name] = [column_name, next(random_thing),
                                             index, '%s,"%s"' % (column_name, index),
                                             '{some value, \\" \' 2}']
                    elif self.test_type == 'dict':
                        line[column_name] = {"column_name": column_name,
                                             "repeater": next(random_thing),
                                             "index": index,
                                             "maybe_hstore": "a => b"}
                    elif self.test_type == 'date':
                        line[column_name] = datetime(2011, (index % 12) + 1,
                                                     next(random_thing), 14,
                                                     30, 25)
                    elif self.test_type == 'int':
                        line[column_name] = index
                    elif self.test_type == 'encoding':
                        line[column_name] = b'\xc3\xa9\xc3\xa0\xc2\xa4'.decode('utf-8')
                    elif self.test_type == 'nested_list':
                        line[column_name] = [[column_name], [next(random_thing), '{some value, \\" 2}'],
                                             [index, '%s,"%s"' % (column_name, index)]]
                    else:
                        line[column_name] = '%s %s %s' % (column_name,
                                                          next(random_thing),
                                                          index)
            yield line


    def execute(self, quals, columns):
        log_to_postgres(str(sorted(quals)))
        log_to_postgres(str(sorted(columns)))
        if self.test_type == 'None':
            return None
        elif self.test_type == 'iter_none':
            return [None, None]
        else:
            return self._as_generator(quals, columns)


    def get_rel_size(self, quals, columns):
        if self.test_type == 'planner':
            return (10000000, len(columns) * 10)
        return (20, len(columns) * 10)

    def get_path_keys(self):
        if self.test_type == 'planner':
            return [(('test1',), 1)]
        return []

    def update(self, rowid, newvalues):
        if self.test_type == 'nowrite':
            super(TestForeignDataWrapper, self).update(rowid, newvalues)
        log_to_postgres("UPDATING: %s with %s" % (
            rowid, sorted(newvalues.items())))
        if self.test_type == 'returning':
            for key in newvalues:
                newvalues[key] = "UPDATED: %s" % newvalues[key]
            return newvalues

    def delete(self, rowid):
        if self.test_type == 'nowrite':
            super(TestForeignDataWrapper, self).delete(rowid)
        log_to_postgres("DELETING: %s" % rowid)

    def insert(self, values):
        if self.test_type == 'nowrite':
            super(TestForeignDataWrapper, self).insert(values)
        log_to_postgres("INSERTING: %s" % sorted(values.items()))
        if self.test_type == 'returning':
            for key in self.columns:
                values[key] = "INSERTED: %s" % values.get(key, None)
            return values

    @property
    def rowid_column(self):
        return self._row_id_column

    def begin(self, serializable):
        if self.tx_hook:
            log_to_postgres('BEGIN')

    def sub_begin(self, level):
        if self.tx_hook:
            log_to_postgres('SUBBEGIN')

    def sub_rollback(self, level):
        if self.tx_hook:
            log_to_postgres('SUBROLLBACK')

    def sub_commit(self, level):
        if self.tx_hook:
            log_to_postgres('SUBCOMMIT')

    def commit(self):
        if self.tx_hook:
            log_to_postgres('COMMIT')

    def pre_commit(self):
        if self.tx_hook:
            log_to_postgres('PRECOMMIT')

    def rollback(self):
        if self.tx_hook:
            log_to_postgres('ROLLBACK')

########NEW FILE########
__FILENAME__ = utils
from logging import ERROR, INFO, DEBUG, WARNING, CRITICAL
try:
    from ._utils import _log_to_postgres
except ImportError as e:
    from warnings import warn
    warn("Not executed in a postgresql server,"
         " disabling log_to_postgres", ImportWarning)

    def _log_to_postgres(message, level=0, hint=None, detail=None):
        pass


REPORT_CODES = {
        DEBUG: 0,
        INFO: 1,
        WARNING: 2,
        ERROR: 3,
        CRITICAL: 4
}


def log_to_postgres(message, level=INFO, hint=None, detail=None):
    code = REPORT_CODES.get(level, None)
    if code is None:
        raise KeyError("Not a valid log level")
    _log_to_postgres(message, code, hint=hint, detail=detail)

########NEW FILE########
__FILENAME__ = xmlfdw
"""
An XML Foreign Data Wrapper.
"""

from . import ForeignDataWrapper
from xml.sax import ContentHandler, make_parser

class MulticornXMLHandler(ContentHandler):

    def __init__(self, elem_tag, columns):
        self.elem_tag = elem_tag
        self.columns = columns
        self.reset()

    def reset(self):
        self.parsed_rows = []
        self.current_row = {}
        self.tag = None
        self.root_seen = 0
        self.nested = False

    def startElement(self, name, attrs):
        if name == self.elem_tag:
            # Keep track of nested "elem_tag"
            self.root_seen += 1
        elif self.root_seen == 1:
            # Ignore nested tag.
            if name in self.columns:
                self.tag = name
                self.current_row[name] = ''

    def characters(self, content):
        if self.tag is not None:
            self.current_row[self.tag] += content

    def get_rows(self):
        """Return the parsed_rows, and forget about it."""
        result, self.parsed_rows = self.parsed_rows, []
        return result

    def endElement(self, name):
        if name == self.elem_tag:
            self.root_seen -= 1
            self.parsed_rows.append(self.current_row)
            self.current_row = {}
        elif name in self.columns:
            self.tag = None

class XMLFdw(ForeignDataWrapper):
    """A foreign data wrapper for accessing xml files.

      Valid options:
        - filename: full path to the xml file.
        - elem_tag: a tagname acting as a root for a tag.
               Child tag will be mapped to corresponding columns.
    """

    def __init__(self, fdw_options, fdw_columns):
        super(XMLFdw, self).__init__(fdw_options, fdw_columns)
        self.filename = fdw_options['filename']
        self.elem_tag = fdw_options['elem_tag']
        self.buffer_size = fdw_options.get('buffer_size', 4096)
        self.columns = fdw_columns

    def execute(self, quals, columns):
        parser = make_parser()
        handler = MulticornXMLHandler(self.elem_tag, self.columns)
        parser.setContentHandler(handler)
        with open(self.filename) as stream:
            while(True):
                a = stream.read(self.buffer_size)
                if not a:
                    break
                parser.feed(a)
                for row in handler.get_rows():
                    yield row
        parser.close()

########NEW FILE########
