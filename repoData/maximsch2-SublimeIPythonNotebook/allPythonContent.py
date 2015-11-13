__FILENAME__ = data
# encoding: utf-8
"""Utilities for working with data structures like lists, dicts and tuples.
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

def uniq_stable(elems):
    """uniq_stable(elems) -> list

    Return from an iterable, a list of all the unique elements in the input,
    but maintaining the order in which they first appear.

    Note: All elements in the input must be hashable for this routine
    to work, as it internally uses a set for efficiency reasons.
    """
    seen = set()
    return [x for x in elems if x not in seen and not seen.add(x)]


def flatten(seq):
    """Flatten a list of lists (NOT recursive, only works for 2d lists)."""

    return [x for subseq in seq for x in subseq]
    

def chop(seq, size):
    """Chop a sequence into chunks of the given size."""
    return [seq[i:i+size] for i in xrange(0,len(seq),size)]



########NEW FILE########
__FILENAME__ = encoding
# coding: utf-8
"""
Utilities for dealing with text encodings
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2012  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
import sys
import locale

# to deal with the possibility of sys.std* not being a stream at all
def get_stream_enc(stream, default=None):
    """Return the given stream's encoding or a default.

    There are cases where ``sys.std*`` might not actually be a stream, so
    check for the encoding attribute prior to returning it, and return
    a default if it doesn't exist or evaluates as False. ``default``
    is None if not provided.
    """
    if not hasattr(stream, 'encoding') or not stream.encoding:
        return default
    else:
        return stream.encoding

# Less conservative replacement for sys.getdefaultencoding, that will try
# to match the environment.
# Defined here as central function, so if we find better choices, we
# won't need to make changes all over IPython.
def getdefaultencoding():
    """Return IPython's guess for the default encoding for bytes as text.

    Asks for stdin.encoding first, to match the calling Terminal, but that
    is often None for subprocesses.  Fall back on locale.getpreferredencoding()
    which should be a sensible platform default (that respects LANG environment),
    and finally to sys.getdefaultencoding() which is the most conservative option,
    and usually ASCII.
    """
    enc = get_stream_enc(sys.stdin)
    if not enc or enc=='ascii':
        try:
            # There are reports of getpreferredencoding raising errors
            # in some cases, which may well be fixed, but let's be conservative here.
            enc = locale.getpreferredencoding()
        except Exception:
            pass
    return enc or sys.getdefaultencoding()

DEFAULT_ENCODING = getdefaultencoding()

########NEW FILE########
__FILENAME__ = ipstruct
# encoding: utf-8
"""A dict subclass that supports attribute style access.

Authors:

* Fernando Perez (original)
* Brian Granger (refactoring to a dict subclass)
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

__all__ = ['Struct']

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------


class Struct(dict):
    """A dict subclass with attribute style access.

    This dict subclass has a a few extra features:

    * Attribute style access.
    * Protection of class members (like keys, items) when using attribute
      style access.
    * The ability to restrict assignment to only existing keys.
    * Intelligent merging.
    * Overloaded operators.
    """
    _allownew = True
    def __init__(self, *args, **kw):
        """Initialize with a dictionary, another Struct, or data.

        Parameters
        ----------
        args : dict, Struct
            Initialize with one dict or Struct
        kw : dict
            Initialize with key, value pairs.

        Examples
        --------

        >>> s = Struct(a=10,b=30)
        >>> s.a
        10
        >>> s.b
        30
        >>> s2 = Struct(s,c=30)
        >>> sorted(s2.keys())
        ['a', 'b', 'c']
        """
        object.__setattr__(self, '_allownew', True)
        dict.__init__(self, *args, **kw)

    def __setitem__(self, key, value):
        """Set an item with check for allownew.

        Examples
        --------

        >>> s = Struct()
        >>> s['a'] = 10
        >>> s.allow_new_attr(False)
        >>> s['a'] = 10
        >>> s['a']
        10
        >>> try:
        ...     s['b'] = 20
        ... except KeyError:
        ...     print 'this is not allowed'
        ...
        this is not allowed
        """
        if not self._allownew and key not in self:
            raise KeyError(
                "can't create new attribute %s when allow_new_attr(False)" % key)
        dict.__setitem__(self, key, value)

    def __setattr__(self, key, value):
        """Set an attr with protection of class members.

        This calls :meth:`self.__setitem__` but convert :exc:`KeyError` to
        :exc:`AttributeError`.

        Examples
        --------

        >>> s = Struct()
        >>> s.a = 10
        >>> s.a
        10
        >>> try:
        ...     s.get = 10
        ... except AttributeError:
        ...     print "you can't set a class member"
        ...
        you can't set a class member
        """
        # If key is an str it might be a class member or instance var
        if isinstance(key, str):
            # I can't simply call hasattr here because it calls getattr, which
            # calls self.__getattr__, which returns True for keys in
            # self._data.  But I only want keys in the class and in
            # self.__dict__
            if key in self.__dict__ or hasattr(Struct, key):
                raise AttributeError(
                    'attr %s is a protected member of class Struct.' % key
                )
        try:
            self.__setitem__(key, value)
        except KeyError as e:
            raise AttributeError(e)

    def __getattr__(self, key):
        """Get an attr by calling :meth:`dict.__getitem__`.

        Like :meth:`__setattr__`, this method converts :exc:`KeyError` to
        :exc:`AttributeError`.

        Examples
        --------

        >>> s = Struct(a=10)
        >>> s.a
        10
        >>> type(s.get)
        <... 'builtin_function_or_method'>
        >>> try:
        ...     s.b
        ... except AttributeError:
        ...     print "I don't have that key"
        ...
        I don't have that key
        """
        try:
            result = self[key]
        except KeyError:
            raise AttributeError(key)
        else:
            return result

    def __iadd__(self, other):
        """s += s2 is a shorthand for s.merge(s2).

        Examples
        --------

        >>> s = Struct(a=10,b=30)
        >>> s2 = Struct(a=20,c=40)
        >>> s += s2
        >>> sorted(s.keys())
        ['a', 'b', 'c']
        """
        self.merge(other)
        return self

    def __add__(self,other):
        """s + s2 -> New Struct made from s.merge(s2).

        Examples
        --------

        >>> s1 = Struct(a=10,b=30)
        >>> s2 = Struct(a=20,c=40)
        >>> s = s1 + s2
        >>> sorted(s.keys())
        ['a', 'b', 'c']
        """
        sout = self.copy()
        sout.merge(other)
        return sout

    def __sub__(self,other):
        """s1 - s2 -> remove keys in s2 from s1.

        Examples
        --------

        >>> s1 = Struct(a=10,b=30)
        >>> s2 = Struct(a=40)
        >>> s = s1 - s2
        >>> s
        {'b': 30}
        """
        sout = self.copy()
        sout -= other
        return sout

    def __isub__(self,other):
        """Inplace remove keys from self that are in other.

        Examples
        --------

        >>> s1 = Struct(a=10,b=30)
        >>> s2 = Struct(a=40)
        >>> s1 -= s2
        >>> s1
        {'b': 30}
        """
        for k in other.keys():
            if k in self:
                del self[k]
        return self

    def __dict_invert(self, data):
        """Helper function for merge.

        Takes a dictionary whose values are lists and returns a dict with
        the elements of each list as keys and the original keys as values.
        """
        outdict = {}
        for k,lst in data.items():
            if isinstance(lst, str):
                lst = lst.split()
            for entry in lst:
                outdict[entry] = k
        return outdict

    def dict(self):
        return self

    def copy(self):
        """Return a copy as a Struct.

        Examples
        --------

        >>> s = Struct(a=10,b=30)
        >>> s2 = s.copy()
        >>> type(s2) is Struct
        True
        """
        return Struct(dict.copy(self))

    def hasattr(self, key):
        """hasattr function available as a method.

        Implemented like has_key.

        Examples
        --------

        >>> s = Struct(a=10)
        >>> s.hasattr('a')
        True
        >>> s.hasattr('b')
        False
        >>> s.hasattr('get')
        False
        """
        return key in self

    def allow_new_attr(self, allow = True):
        """Set whether new attributes can be created in this Struct.

        This can be used to catch typos by verifying that the attribute user
        tries to change already exists in this Struct.
        """
        object.__setattr__(self, '_allownew', allow)

    def merge(self, __loc_data__=None, __conflict_solve=None, **kw):
        """Merge two Structs with customizable conflict resolution.

        This is similar to :meth:`update`, but much more flexible. First, a
        dict is made from data+key=value pairs. When merging this dict with
        the Struct S, the optional dictionary 'conflict' is used to decide
        what to do.

        If conflict is not given, the default behavior is to preserve any keys
        with their current value (the opposite of the :meth:`update` method's
        behavior).

        Parameters
        ----------
        __loc_data : dict, Struct
            The data to merge into self
        __conflict_solve : dict
            The conflict policy dict.  The keys are binary functions used to
            resolve the conflict and the values are lists of strings naming
            the keys the conflict resolution function applies to.  Instead of
            a list of strings a space separated string can be used, like
            'a b c'.
        kw : dict
            Additional key, value pairs to merge in

        Notes
        -----

        The `__conflict_solve` dict is a dictionary of binary functions which will be used to
        solve key conflicts.  Here is an example::

            __conflict_solve = dict(
                func1=['a','b','c'],
                func2=['d','e']
            )

        In this case, the function :func:`func1` will be used to resolve
        keys 'a', 'b' and 'c' and the function :func:`func2` will be used for
        keys 'd' and 'e'.  This could also be written as::

            __conflict_solve = dict(func1='a b c',func2='d e')

        These functions will be called for each key they apply to with the
        form::

            func1(self['a'], other['a'])

        The return value is used as the final merged value.

        As a convenience, merge() provides five (the most commonly needed)
        pre-defined policies: preserve, update, add, add_flip and add_s. The
        easiest explanation is their implementation::

            preserve = lambda old,new: old
            update   = lambda old,new: new
            add      = lambda old,new: old + new
            add_flip = lambda old,new: new + old  # note change of order!
            add_s    = lambda old,new: old + ' ' + new  # only for str!

        You can use those four words (as strings) as keys instead
        of defining them as functions, and the merge method will substitute
        the appropriate functions for you.

        For more complicated conflict resolution policies, you still need to
        construct your own functions.

        Examples
        --------

        This show the default policy:

        >>> s = Struct(a=10,b=30)
        >>> s2 = Struct(a=20,c=40)
        >>> s.merge(s2)
        >>> sorted(s.items())
        [('a', 10), ('b', 30), ('c', 40)]

        Now, show how to specify a conflict dict:

        >>> s = Struct(a=10,b=30)
        >>> s2 = Struct(a=20,b=40)
        >>> conflict = {'update':'a','add':'b'}
        >>> s.merge(s2,conflict)
        >>> sorted(s.items())
        [('a', 20), ('b', 70)]
        """

        data_dict = dict(__loc_data__,**kw)

        # policies for conflict resolution: two argument functions which return
        # the value that will go in the new struct
        preserve = lambda old,new: old
        update   = lambda old,new: new
        add      = lambda old,new: old + new
        add_flip = lambda old,new: new + old  # note change of order!
        add_s    = lambda old,new: old + ' ' + new

        # default policy is to keep current keys when there's a conflict
        conflict_solve = dict.fromkeys(self, preserve)

        # the conflict_solve dictionary is given by the user 'inverted': we
        # need a name-function mapping, it comes as a function -> names
        # dict. Make a local copy (b/c we'll make changes), replace user
        # strings for the three builtin policies and invert it.
        if __conflict_solve:
            inv_conflict_solve_user = __conflict_solve.copy()
            for name, func in [('preserve',preserve), ('update',update),
                               ('add',add), ('add_flip',add_flip),
                               ('add_s',add_s)]:
                if name in inv_conflict_solve_user.keys():
                    inv_conflict_solve_user[func] = inv_conflict_solve_user[name]
                    del inv_conflict_solve_user[name]
            conflict_solve.update(self.__dict_invert(inv_conflict_solve_user))
        for key in data_dict:
            if key not in self:
                self[key] = data_dict[key]
            else:
                self[key] = conflict_solve[key](self[key],data_dict[key])


########NEW FILE########
__FILENAME__ = nbbase
"""The basic dict based notebook format.

The Python representation of a notebook is a nested structure of
dictionary subclasses that support attribute access
(.ipstruct.Struct). The functions in this module are merely
helpers to build the structs in the right form.

Authors:

* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import pprint
import uuid

from .ipstruct import Struct

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

# Change this when incrementing the nbformat version
nbformat = 3
nbformat_minor = 0

class NotebookNode(Struct):
    pass


def from_dict(d):
    if isinstance(d, dict):
        newd = NotebookNode()
        for k,v in d.items():
            newd[k] = from_dict(v)
        return newd
    elif isinstance(d, (tuple, list)):
        return [from_dict(i) for i in d]
    else:
        return d


def new_output(output_type=None, output_text=None, output_png=None,
    output_html=None, output_svg=None, output_latex=None, output_json=None,
    output_javascript=None, output_jpeg=None, prompt_number=None,
    ename=None, evalue=None, traceback=None, stream=None, metadata=None):
    """Create a new code cell with input and output"""
    output = NotebookNode()
    if output_type is not None:
        output.output_type = unicode(output_type)

    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise TypeError("metadata must be dict")
    output.metadata = metadata

    if output_type != 'pyerr':
        if output_text is not None:
            output.text = unicode(output_text)
        if output_png is not None:
            output.png = bytes(output_png)
        if output_jpeg is not None:
            output.jpeg = bytes(output_jpeg)
        if output_html is not None:
            output.html = unicode(output_html)
        if output_svg is not None:
            output.svg = unicode(output_svg)
        if output_latex is not None:
            output.latex = unicode(output_latex)
        if output_json is not None:
            output.json = unicode(output_json)
        if output_javascript is not None:
            output.javascript = unicode(output_javascript)

    if output_type == u'pyout':
        if prompt_number is not None:
            output.prompt_number = int(prompt_number)

    if output_type == u'pyerr':
        if ename is not None:
            output.ename = unicode(ename)
        if evalue is not None:
            output.evalue = unicode(evalue)
        if traceback is not None:
            output.traceback = [unicode(frame) for frame in list(traceback)]

    if output_type == u'stream':
        output.stream = 'stdout' if stream is None else unicode(stream)
    
    return output


def new_code_cell(input=None, prompt_number=None, outputs=None,
    language=u'python', collapsed=False, metadata=None):
    """Create a new code cell with input and output"""
    cell = NotebookNode()
    cell.cell_type = u'code'
    if language is not None:
        cell.language = unicode(language)
    if input is not None:
        cell.input = unicode(input)
    if prompt_number is not None:
        cell.prompt_number = int(prompt_number)
    if outputs is None:
        cell.outputs = []
    else:
        cell.outputs = outputs
    if collapsed is not None:
        cell.collapsed = bool(collapsed)
    cell.metadata = NotebookNode(metadata or {})

    return cell

def new_text_cell(cell_type, source=None, rendered=None, metadata=None):
    """Create a new text cell."""
    cell = NotebookNode()
    # VERSIONHACK: plaintext -> raw
    # handle never-released plaintext name for raw cells
    if cell_type == 'plaintext':
        cell_type = 'raw'
    if source is not None:
        cell.source = unicode(source)
    if rendered is not None:
        cell.rendered = unicode(rendered)
    cell.metadata = NotebookNode(metadata or {})
    cell.cell_type = cell_type
    return cell


def new_heading_cell(source=None, rendered=None, level=1, metadata=None):
    """Create a new section cell with a given integer level."""
    cell = NotebookNode()
    cell.cell_type = u'heading'
    if source is not None:
        cell.source = unicode(source)
    if rendered is not None:
        cell.rendered = unicode(rendered)
    cell.level = int(level)
    cell.metadata = NotebookNode(metadata or {})
    return cell


def new_worksheet(name=None, cells=None, metadata=None):
    """Create a worksheet by name with with a list of cells."""
    ws = NotebookNode()
    if name is not None:
        ws.name = unicode(name)
    if cells is None:
        ws.cells = []
    else:
        ws.cells = list(cells)
    ws.metadata = NotebookNode(metadata or {})
    return ws


def new_notebook(name=None, metadata=None, worksheets=None):
    """Create a notebook by name, id and a list of worksheets."""
    nb = NotebookNode()
    nb.nbformat = nbformat
    nb.nbformat_minor = nbformat_minor
    if worksheets is None:
        nb.worksheets = []
    else:
        nb.worksheets = list(worksheets)
    if metadata is None:
        nb.metadata = new_metadata()
    else:
        nb.metadata = NotebookNode(metadata)
    if name is not None:
        nb.metadata.name = unicode(name)
    return nb


def new_metadata(name=None, authors=None, license=None, created=None,
    modified=None, gistid=None):
    """Create a new metadata node."""
    metadata = NotebookNode()
    if name is not None:
        metadata.name = unicode(name)
    if authors is not None:
        metadata.authors = list(authors)
    if created is not None:
        metadata.created = unicode(created)
    if modified is not None:
        metadata.modified = unicode(modified)
    if license is not None:
        metadata.license = unicode(license)
    if gistid is not None:
        metadata.gistid = unicode(gistid)
    return metadata

def new_author(name=None, email=None, affiliation=None, url=None):
    """Create a new author."""
    author = NotebookNode()
    if name is not None:
        author.name = unicode(name)
    if email is not None:
        author.email = unicode(email)
    if affiliation is not None:
        author.affiliation = unicode(affiliation)
    if url is not None:
        author.url = unicode(url)
    return author


########NEW FILE########
__FILENAME__ = nbjson
"""Read and write notebooks in JSON format.

Authors:

* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import copy
import json

from .nbbase import from_dict
from .rwbase import (
    NotebookReader, NotebookWriter, restore_bytes, rejoin_lines, split_lines
)

from . import py3compat

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

class BytesEncoder(json.JSONEncoder):
    """A JSON encoder that accepts b64 (and other *ascii*) bytestrings."""
    def default(self, obj):
        if isinstance(obj, bytes):
            return obj.decode('ascii')
        return json.JSONEncoder.default(self, obj)


class JSONReader(NotebookReader):

    def reads(self, s, **kwargs):
        nb = json.loads(s, **kwargs)
        nb = self.to_notebook(nb, **kwargs)
        return nb

    def to_notebook(self, d, **kwargs):
        return restore_bytes(rejoin_lines(from_dict(d)))


class JSONWriter(NotebookWriter):

    def writes(self, nb, **kwargs):
        kwargs['cls'] = BytesEncoder
        kwargs['indent'] = 1
        kwargs['sort_keys'] = True
        kwargs['separators'] = (',',': ')
        if kwargs.pop('split_lines', True):
            nb = split_lines(copy.deepcopy(nb))
        return py3compat.str_to_unicode(json.dumps(nb, **kwargs), 'utf-8')
    

_reader = JSONReader()
_writer = JSONWriter()

reads = _reader.reads
read = _reader.read
to_notebook = _reader.to_notebook
write = _writer.write
writes = _writer.writes


########NEW FILE########
__FILENAME__ = nbpy
"""Read and write notebooks as regular .py files.

Authors:

* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import re
from .rwbase import NotebookReader, NotebookWriter
from .nbbase import (
    new_code_cell, new_text_cell, new_worksheet,
    new_notebook, new_heading_cell, nbformat, nbformat_minor,
)

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

_encoding_declaration_re = re.compile(r"^#.*coding[:=]\s*([-\w.]+)")

class PyReaderError(Exception):
    pass


class PyReader(NotebookReader):

    def reads(self, s, **kwargs):
        return self.to_notebook(s,**kwargs)

    def to_notebook(self, s, **kwargs):
        lines = s.splitlines()
        cells = []
        cell_lines = []
        kwargs = {}
        state = u'codecell'
        for line in lines:
            if line.startswith(u'# <nbformat>') or _encoding_declaration_re.match(line):
                pass
            elif line.startswith(u'# <codecell>'):
                cell = self.new_cell(state, cell_lines, **kwargs)
                if cell is not None:
                    cells.append(cell)
                state = u'codecell'
                cell_lines = []
                kwargs = {}
            elif line.startswith(u'# <htmlcell>'):
                cell = self.new_cell(state, cell_lines, **kwargs)
                if cell is not None:
                    cells.append(cell)
                state = u'htmlcell'
                cell_lines = []
                kwargs = {}
            elif line.startswith(u'# <markdowncell>'):
                cell = self.new_cell(state, cell_lines, **kwargs)
                if cell is not None:
                    cells.append(cell)
                state = u'markdowncell'
                cell_lines = []
                kwargs = {}
            # VERSIONHACK: plaintext -> raw
            elif line.startswith(u'# <rawcell>') or line.startswith(u'# <plaintextcell>'):
                cell = self.new_cell(state, cell_lines, **kwargs)
                if cell is not None:
                    cells.append(cell)
                state = u'rawcell'
                cell_lines = []
                kwargs = {}
            elif line.startswith(u'# <headingcell'):
                cell = self.new_cell(state, cell_lines, **kwargs)
                if cell is not None:
                    cells.append(cell)
                    cell_lines = []
                m = re.match(r'# <headingcell level=(?P<level>\d)>',line)
                if m is not None:
                    state = u'headingcell'
                    kwargs = {}
                    kwargs['level'] = int(m.group('level'))
                else:
                    state = u'codecell'
                    kwargs = {}
                    cell_lines = []
            else:
                cell_lines.append(line)
        if cell_lines and state == u'codecell':
            cell = self.new_cell(state, cell_lines)
            if cell is not None:
                cells.append(cell)
        ws = new_worksheet(cells=cells)
        nb = new_notebook(worksheets=[ws])
        return nb

    def new_cell(self, state, lines, **kwargs):
        if state == u'codecell':
            input = u'\n'.join(lines)
            input = input.strip(u'\n')
            if input:
                return new_code_cell(input=input)
        elif state == u'htmlcell':
            text = self._remove_comments(lines)
            if text:
                return new_text_cell(u'html',source=text)
        elif state == u'markdowncell':
            text = self._remove_comments(lines)
            if text:
                return new_text_cell(u'markdown',source=text)
        elif state == u'rawcell':
            text = self._remove_comments(lines)
            if text:
                return new_text_cell(u'raw',source=text)
        elif state == u'headingcell':
            text = self._remove_comments(lines)
            level = kwargs.get('level',1)
            if text:
                return new_heading_cell(source=text,level=level)

    def _remove_comments(self, lines):
        new_lines = []
        for line in lines:
            if line.startswith(u'#'):
                new_lines.append(line[2:])
            else:
                new_lines.append(line)
        text = u'\n'.join(new_lines)
        text = text.strip(u'\n')
        return text

    def split_lines_into_blocks(self, lines):
        if len(lines) == 1:
            yield lines[0]
            raise StopIteration()
        import ast
        source = '\n'.join(lines)
        code = ast.parse(source)
        starts = [x.lineno-1 for x in code.body]
        for i in range(len(starts)-1):
            yield '\n'.join(lines[starts[i]:starts[i+1]]).strip('\n')
        yield '\n'.join(lines[starts[-1]:]).strip('\n')


class PyWriter(NotebookWriter):

    def writes(self, nb, **kwargs):
        lines = [u'# -*- coding: utf-8 -*-']
        lines.extend([
            u'# <nbformat>%i.%i</nbformat>' % (nbformat, nbformat_minor),
            u'',
        ])
        for ws in nb.worksheets:
            for cell in ws.cells:
                if cell.cell_type == u'code':
                    input = cell.get(u'input')
                    if input is not None:
                        lines.extend([u'# <codecell>',u''])
                        lines.extend(input.splitlines())
                        lines.append(u'')
                elif cell.cell_type == u'html':
                    input = cell.get(u'source')
                    if input is not None:
                        lines.extend([u'# <htmlcell>',u''])
                        lines.extend([u'# ' + line for line in input.splitlines()])
                        lines.append(u'')
                elif cell.cell_type == u'markdown':
                    input = cell.get(u'source')
                    if input is not None:
                        lines.extend([u'# <markdowncell>',u''])
                        lines.extend([u'# ' + line for line in input.splitlines()])
                        lines.append(u'')
                elif cell.cell_type == u'raw':
                    input = cell.get(u'source')
                    if input is not None:
                        lines.extend([u'# <rawcell>',u''])
                        lines.extend([u'# ' + line for line in input.splitlines()])
                        lines.append(u'')
                elif cell.cell_type == u'heading':
                    input = cell.get(u'source')
                    level = cell.get(u'level',1)
                    if input is not None:
                        lines.extend([u'# <headingcell level=%s>' % level,u''])
                        lines.extend([u'# ' + line for line in input.splitlines()])
                        lines.append(u'')
        lines.append('')
        return unicode('\n'.join(lines))


_reader = PyReader()
_writer = PyWriter()

reads = _reader.reads
read = _reader.read
to_notebook = _reader.to_notebook
write = _writer.write
writes = _writer.writes


########NEW FILE########
__FILENAME__ = py3compat
# coding: utf-8
"""Compatibility tricks for Python 3. Mainly to do with unicode."""
import __builtin__
import functools
import sys
import re
import types

from .encoding import DEFAULT_ENCODING

orig_open = open

def no_code(x, encoding=None):
    return x

def decode(s, encoding=None):
    encoding = encoding or DEFAULT_ENCODING
    return s.decode(encoding, "replace")

def encode(u, encoding=None):
    encoding = encoding or DEFAULT_ENCODING
    return u.encode(encoding, "replace")


def cast_unicode(s, encoding=None):
    if isinstance(s, bytes):
        return decode(s, encoding)
    return s

def cast_bytes(s, encoding=None):
    if not isinstance(s, bytes):
        return encode(s, encoding)
    return s

def _modify_str_or_docstring(str_change_func):
    @functools.wraps(str_change_func)
    def wrapper(func_or_str):
        if isinstance(func_or_str, basestring):
            func = None
            doc = func_or_str
        else:
            func = func_or_str
            doc = func.__doc__
        
        doc = str_change_func(doc)
        
        if func:
            func.__doc__ = doc
            return func
        return doc
    return wrapper

if sys.version_info[0] >= 3:
    PY3 = True
    
    input = input
    builtin_mod_name = "builtins"
    
    str_to_unicode = no_code
    unicode_to_str = no_code
    str_to_bytes = encode
    bytes_to_str = decode
    cast_bytes_py2 = no_code
    
    string_types = (str,)
    
    def isidentifier(s, dotted=False):
        if dotted:
            return all(isidentifier(a) for a in s.split("."))
        return s.isidentifier()
    
    open = orig_open
    
    MethodType = types.MethodType
    
    def execfile(fname, glob, loc=None):
        loc = loc if (loc is not None) else glob
        with open(fname, 'rb') as f:
            exec compile(f.read(), fname, 'exec') in glob, loc
    
    # Refactor print statements in doctests.
    _print_statement_re = re.compile(r"\bprint (?P<expr>.*)$", re.MULTILINE)
    def _print_statement_sub(match):
        expr = match.groups('expr')
        return "print(%s)" % expr
    
    @_modify_str_or_docstring
    def doctest_refactor_print(doc):
        """Refactor 'print x' statements in a doctest to print(x) style. 2to3
        unfortunately doesn't pick up on our doctests.
        
        Can accept a string or a function, so it can be used as a decorator."""
        return _print_statement_re.sub(_print_statement_sub, doc)
    
    # Abstract u'abc' syntax:
    @_modify_str_or_docstring
    def u_format(s):
        """"{u}'abc'" --> "'abc'" (Python 3)
        
        Accepts a string or a function, so it can be used as a decorator."""
        return s.format(u='')

else:
    PY3 = False
    
    input = raw_input
    builtin_mod_name = "__builtin__"
    
    str_to_unicode = decode
    unicode_to_str = encode
    str_to_bytes = no_code
    bytes_to_str = no_code
    cast_bytes_py2 = cast_bytes
    
    string_types = (str, unicode)
    
    import re
    _name_re = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*$")
    def isidentifier(s, dotted=False):
        if dotted:
            return all(isidentifier(a) for a in s.split("."))
        return bool(_name_re.match(s))
    
    class open(object):
        """Wrapper providing key part of Python 3 open() interface."""
        def __init__(self, fname, mode="r", encoding="utf-8"):
            self.f = orig_open(fname, mode)
            self.enc = encoding
        
        def write(self, s):
            return self.f.write(s.encode(self.enc))
        
        def read(self, size=-1):
            return self.f.read(size).decode(self.enc)
        
        def close(self):
            return self.f.close()
        
        def __enter__(self):
            return self
        
        def __exit__(self, etype, value, traceback):
            self.f.close()
    
    def MethodType(func, instance):
        return types.MethodType(func, instance, type(instance))
    
    # don't override system execfile on 2.x:
    execfile = execfile
    
    def doctest_refactor_print(func_or_str):
        return func_or_str


    # Abstract u'abc' syntax:
    @_modify_str_or_docstring
    def u_format(s):
        """"{u}'abc'" --> "u'abc'" (Python 2)
        
        Accepts a string or a function, so it can be used as a decorator."""
        return s.format(u='u')

    if sys.platform == 'win32':
        def execfile(fname, glob=None, loc=None):
            loc = loc if (loc is not None) else glob
            # The rstrip() is necessary b/c trailing whitespace in files will
            # cause an IndentationError in Python 2.6 (this was fixed in 2.7,
            # but we still support 2.6).  See issue 1027.
            scripttext = __builtin__.open(fname).read().rstrip() + '\n'
            # compile converts unicode filename to str assuming
            # ascii. Let's do the conversion before calling compile
            if isinstance(fname, unicode):
                filename = unicode_to_str(fname)
            else:
                filename = fname
            exec compile(scripttext, filename, 'exec') in glob, loc
    else:
        def execfile(fname, *where):
            if isinstance(fname, unicode):
                filename = fname.encode(sys.getfilesystemencoding())
            else:
                filename = fname
            __builtin__.execfile(filename, *where)

########NEW FILE########
__FILENAME__ = rwbase
"""Base classes and utilities for readers and writers.

Authors:

* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from base64 import encodestring, decodestring
import pprint

from . import py3compat

str_to_bytes = py3compat.str_to_bytes

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

def restore_bytes(nb):
    """Restore bytes of image data from unicode-only formats.
    
    Base64 encoding is handled elsewhere.  Bytes objects in the notebook are
    always b64-encoded. We DO NOT encode/decode around file formats.
    """
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                for output in cell.outputs:
                    if 'png' in output:
                        output.png = str_to_bytes(output.png, 'ascii')
                    if 'jpeg' in output:
                        output.jpeg = str_to_bytes(output.jpeg, 'ascii')
    return nb

# output keys that are likely to have multiline values
_multiline_outputs = ['text', 'html', 'svg', 'latex', 'javascript', 'json']


# FIXME: workaround for old splitlines()
def _join_lines(lines):
    """join lines that have been written by splitlines()
    
    Has logic to protect against `splitlines()`, which
    should have been `splitlines(True)`
    """
    if lines and lines[0].endswith(('\n', '\r')):
        # created by splitlines(True)
        return u''.join(lines)
    else:
        # created by splitlines()
        return u'\n'.join(lines)


def rejoin_lines(nb):
    """rejoin multiline text into strings
    
    For reversing effects of ``split_lines(nb)``.
    
    This only rejoins lines that have been split, so if text objects were not split
    they will pass through unchanged.
    
    Used when reading JSON files that may have been passed through split_lines.
    """
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                if 'input' in cell and isinstance(cell.input, list):
                    cell.input = _join_lines(cell.input)
                for output in cell.outputs:
                    for key in _multiline_outputs:
                        item = output.get(key, None)
                        if isinstance(item, list):
                            output[key] = _join_lines(item)
            else: # text, heading cell
                for key in ['source', 'rendered']:
                    item = cell.get(key, None)
                    if isinstance(item, list):
                        cell[key] = _join_lines(item)
    return nb


def split_lines(nb):
    """split likely multiline text into lists of strings
    
    For file output more friendly to line-based VCS. ``rejoin_lines(nb)`` will
    reverse the effects of ``split_lines(nb)``.
    
    Used when writing JSON files.
    """
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                if 'input' in cell and isinstance(cell.input, basestring):
                    cell.input = cell.input.splitlines(True)
                for output in cell.outputs:
                    for key in _multiline_outputs:
                        item = output.get(key, None)
                        if isinstance(item, basestring):
                            output[key] = item.splitlines(True)
            else: # text, heading cell
                for key in ['source', 'rendered']:
                    item = cell.get(key, None)
                    if isinstance(item, basestring):
                        cell[key] = item.splitlines(True)
    return nb

# b64 encode/decode are never actually used, because all bytes objects in
# the notebook are already b64-encoded, and we don't need/want to double-encode

def base64_decode(nb):
    """Restore all bytes objects in the notebook from base64-encoded strings.
    
    Note: This is never used
    """
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                for output in cell.outputs:
                    if 'png' in output:
                        if isinstance(output.png, unicode):
                            output.png = output.png.encode('ascii')
                        output.png = decodestring(output.png)
                    if 'jpeg' in output:
                        if isinstance(output.jpeg, unicode):
                            output.jpeg = output.jpeg.encode('ascii')
                        output.jpeg = decodestring(output.jpeg)
    return nb


def base64_encode(nb):
    """Base64 encode all bytes objects in the notebook.
    
    These will be b64-encoded unicode strings
    
    Note: This is never used
    """
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                for output in cell.outputs:
                    if 'png' in output:
                        output.png = encodestring(output.png).decode('ascii')
                    if 'jpeg' in output:
                        output.jpeg = encodestring(output.jpeg).decode('ascii')
    return nb


class NotebookReader(object):
    """A class for reading notebooks."""

    def reads(self, s, **kwargs):
        """Read a notebook from a string."""
        raise NotImplementedError("loads must be implemented in a subclass")

    def read(self, fp, **kwargs):
        """Read a notebook from a file like object"""
        nbs = fp.read()
        if not py3compat.PY3 and not isinstance(nbs, unicode):
            nbs = py3compat.str_to_unicode(nbs)
        return self.reads(nbs, **kwargs)


class NotebookWriter(object):
    """A class for writing notebooks."""

    def writes(self, nb, **kwargs):
        """Write a notebook to a string."""
        raise NotImplementedError("loads must be implemented in a subclass")

    def write(self, nb, fp, **kwargs):
        """Write a notebook to a file like object"""
        nbs = self.writes(nb,**kwargs)
        if not py3compat.PY3 and not isinstance(nbs, unicode):
            # this branch is likely only taken for JSON on Python 2
            nbs = py3compat.str_to_unicode(nbs)
        return fp.write(nbs)




########NEW FILE########
__FILENAME__ = data
# encoding: utf-8
"""Utilities for working with data structures like lists, dicts and tuples.
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

def uniq_stable(elems):
    """uniq_stable(elems) -> list

    Return from an iterable, a list of all the unique elements in the input,
    but maintaining the order in which they first appear.

    Note: All elements in the input must be hashable for this routine
    to work, as it internally uses a set for efficiency reasons.
    """
    seen = set()
    return [x for x in elems if x not in seen and not seen.add(x)]


def flatten(seq):
    """Flatten a list of lists (NOT recursive, only works for 2d lists)."""

    return [x for subseq in seq for x in subseq]
    

def chop(seq, size):
    """Chop a sequence into chunks of the given size."""
    return [seq[i:i+size] for i in range(0,len(seq),size)]



########NEW FILE########
__FILENAME__ = encoding
# coding: utf-8
"""
Utilities for dealing with text encodings
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2012  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
import sys
import locale

# to deal with the possibility of sys.std* not being a stream at all
def get_stream_enc(stream, default=None):
    """Return the given stream's encoding or a default.

    There are cases where ``sys.std*`` might not actually be a stream, so
    check for the encoding attribute prior to returning it, and return
    a default if it doesn't exist or evaluates as False. ``default``
    is None if not provided.
    """
    if not hasattr(stream, 'encoding') or not stream.encoding:
        return default
    else:
        return stream.encoding

# Less conservative replacement for sys.getdefaultencoding, that will try
# to match the environment.
# Defined here as central function, so if we find better choices, we
# won't need to make changes all over IPython.
def getdefaultencoding():
    """Return IPython's guess for the default encoding for bytes as text.

    Asks for stdin.encoding first, to match the calling Terminal, but that
    is often None for subprocesses.  Fall back on locale.getpreferredencoding()
    which should be a sensible platform default (that respects LANG environment),
    and finally to sys.getdefaultencoding() which is the most conservative option,
    and usually ASCII.
    """
    enc = get_stream_enc(sys.stdin)
    if not enc or enc=='ascii':
        try:
            # There are reports of getpreferredencoding raising errors
            # in some cases, which may well be fixed, but let's be conservative here.
            enc = locale.getpreferredencoding()
        except Exception:
            pass
    return enc or sys.getdefaultencoding()

DEFAULT_ENCODING = getdefaultencoding()

########NEW FILE########
__FILENAME__ = ipstruct
# encoding: utf-8
"""A dict subclass that supports attribute style access.

Authors:

* Fernando Perez (original)
* Brian Granger (refactoring to a dict subclass)
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

__all__ = ['Struct']

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------


class Struct(dict):
    """A dict subclass with attribute style access.

    This dict subclass has a a few extra features:

    * Attribute style access.
    * Protection of class members (like keys, items) when using attribute
      style access.
    * The ability to restrict assignment to only existing keys.
    * Intelligent merging.
    * Overloaded operators.
    """
    _allownew = True
    def __init__(self, *args, **kw):
        """Initialize with a dictionary, another Struct, or data.

        Parameters
        ----------
        args : dict, Struct
            Initialize with one dict or Struct
        kw : dict
            Initialize with key, value pairs.

        Examples
        --------

        >>> s = Struct(a=10,b=30)
        >>> s.a
        10
        >>> s.b
        30
        >>> s2 = Struct(s,c=30)
        >>> sorted(s2.keys())
        ['a', 'b', 'c']
        """
        object.__setattr__(self, '_allownew', True)
        dict.__init__(self, *args, **kw)

    def __setitem__(self, key, value):
        """Set an item with check for allownew.

        Examples
        --------

        >>> s = Struct()
        >>> s['a'] = 10
        >>> s.allow_new_attr(False)
        >>> s['a'] = 10
        >>> s['a']
        10
        >>> try:
        ...     s['b'] = 20
        ... except KeyError:
        ...     print 'this is not allowed'
        ...
        this is not allowed
        """
        if not self._allownew and key not in self:
            raise KeyError(
                "can't create new attribute %s when allow_new_attr(False)" % key)
        dict.__setitem__(self, key, value)

    def __setattr__(self, key, value):
        """Set an attr with protection of class members.

        This calls :meth:`self.__setitem__` but convert :exc:`KeyError` to
        :exc:`AttributeError`.

        Examples
        --------

        >>> s = Struct()
        >>> s.a = 10
        >>> s.a
        10
        >>> try:
        ...     s.get = 10
        ... except AttributeError:
        ...     print "you can't set a class member"
        ...
        you can't set a class member
        """
        # If key is an str it might be a class member or instance var
        if isinstance(key, str):
            # I can't simply call hasattr here because it calls getattr, which
            # calls self.__getattr__, which returns True for keys in
            # self._data.  But I only want keys in the class and in
            # self.__dict__
            if key in self.__dict__ or hasattr(Struct, key):
                raise AttributeError(
                    'attr %s is a protected member of class Struct.' % key
                )
        try:
            self.__setitem__(key, value)
        except KeyError as e:
            raise AttributeError(e)

    def __getattr__(self, key):
        """Get an attr by calling :meth:`dict.__getitem__`.

        Like :meth:`__setattr__`, this method converts :exc:`KeyError` to
        :exc:`AttributeError`.

        Examples
        --------

        >>> s = Struct(a=10)
        >>> s.a
        10
        >>> type(s.get)
        <... 'builtin_function_or_method'>
        >>> try:
        ...     s.b
        ... except AttributeError:
        ...     print "I don't have that key"
        ...
        I don't have that key
        """
        try:
            result = self[key]
        except KeyError:
            raise AttributeError(key)
        else:
            return result

    def __iadd__(self, other):
        """s += s2 is a shorthand for s.merge(s2).

        Examples
        --------

        >>> s = Struct(a=10,b=30)
        >>> s2 = Struct(a=20,c=40)
        >>> s += s2
        >>> sorted(s.keys())
        ['a', 'b', 'c']
        """
        self.merge(other)
        return self

    def __add__(self,other):
        """s + s2 -> New Struct made from s.merge(s2).

        Examples
        --------

        >>> s1 = Struct(a=10,b=30)
        >>> s2 = Struct(a=20,c=40)
        >>> s = s1 + s2
        >>> sorted(s.keys())
        ['a', 'b', 'c']
        """
        sout = self.copy()
        sout.merge(other)
        return sout

    def __sub__(self,other):
        """s1 - s2 -> remove keys in s2 from s1.

        Examples
        --------

        >>> s1 = Struct(a=10,b=30)
        >>> s2 = Struct(a=40)
        >>> s = s1 - s2
        >>> s
        {'b': 30}
        """
        sout = self.copy()
        sout -= other
        return sout

    def __isub__(self,other):
        """Inplace remove keys from self that are in other.

        Examples
        --------

        >>> s1 = Struct(a=10,b=30)
        >>> s2 = Struct(a=40)
        >>> s1 -= s2
        >>> s1
        {'b': 30}
        """
        for k in list(other.keys()):
            if k in self:
                del self[k]
        return self

    def __dict_invert(self, data):
        """Helper function for merge.

        Takes a dictionary whose values are lists and returns a dict with
        the elements of each list as keys and the original keys as values.
        """
        outdict = {}
        for k,lst in list(data.items()):
            if isinstance(lst, str):
                lst = lst.split()
            for entry in lst:
                outdict[entry] = k
        return outdict

    def dict(self):
        return self

    def copy(self):
        """Return a copy as a Struct.

        Examples
        --------

        >>> s = Struct(a=10,b=30)
        >>> s2 = s.copy()
        >>> type(s2) is Struct
        True
        """
        return Struct(dict.copy(self))

    def hasattr(self, key):
        """hasattr function available as a method.

        Implemented like has_key.

        Examples
        --------

        >>> s = Struct(a=10)
        >>> s.hasattr('a')
        True
        >>> s.hasattr('b')
        False
        >>> s.hasattr('get')
        False
        """
        return key in self

    def allow_new_attr(self, allow = True):
        """Set whether new attributes can be created in this Struct.

        This can be used to catch typos by verifying that the attribute user
        tries to change already exists in this Struct.
        """
        object.__setattr__(self, '_allownew', allow)

    def merge(self, __loc_data__=None, __conflict_solve=None, **kw):
        """Merge two Structs with customizable conflict resolution.

        This is similar to :meth:`update`, but much more flexible. First, a
        dict is made from data+key=value pairs. When merging this dict with
        the Struct S, the optional dictionary 'conflict' is used to decide
        what to do.

        If conflict is not given, the default behavior is to preserve any keys
        with their current value (the opposite of the :meth:`update` method's
        behavior).

        Parameters
        ----------
        __loc_data : dict, Struct
            The data to merge into self
        __conflict_solve : dict
            The conflict policy dict.  The keys are binary functions used to
            resolve the conflict and the values are lists of strings naming
            the keys the conflict resolution function applies to.  Instead of
            a list of strings a space separated string can be used, like
            'a b c'.
        kw : dict
            Additional key, value pairs to merge in

        Notes
        -----

        The `__conflict_solve` dict is a dictionary of binary functions which will be used to
        solve key conflicts.  Here is an example::

            __conflict_solve = dict(
                func1=['a','b','c'],
                func2=['d','e']
            )

        In this case, the function :func:`func1` will be used to resolve
        keys 'a', 'b' and 'c' and the function :func:`func2` will be used for
        keys 'd' and 'e'.  This could also be written as::

            __conflict_solve = dict(func1='a b c',func2='d e')

        These functions will be called for each key they apply to with the
        form::

            func1(self['a'], other['a'])

        The return value is used as the final merged value.

        As a convenience, merge() provides five (the most commonly needed)
        pre-defined policies: preserve, update, add, add_flip and add_s. The
        easiest explanation is their implementation::

            preserve = lambda old,new: old
            update   = lambda old,new: new
            add      = lambda old,new: old + new
            add_flip = lambda old,new: new + old  # note change of order!
            add_s    = lambda old,new: old + ' ' + new  # only for str!

        You can use those four words (as strings) as keys instead
        of defining them as functions, and the merge method will substitute
        the appropriate functions for you.

        For more complicated conflict resolution policies, you still need to
        construct your own functions.

        Examples
        --------

        This show the default policy:

        >>> s = Struct(a=10,b=30)
        >>> s2 = Struct(a=20,c=40)
        >>> s.merge(s2)
        >>> sorted(s.items())
        [('a', 10), ('b', 30), ('c', 40)]

        Now, show how to specify a conflict dict:

        >>> s = Struct(a=10,b=30)
        >>> s2 = Struct(a=20,b=40)
        >>> conflict = {'update':'a','add':'b'}
        >>> s.merge(s2,conflict)
        >>> sorted(s.items())
        [('a', 20), ('b', 70)]
        """

        data_dict = dict(__loc_data__,**kw)

        # policies for conflict resolution: two argument functions which return
        # the value that will go in the new struct
        preserve = lambda old,new: old
        update   = lambda old,new: new
        add      = lambda old,new: old + new
        add_flip = lambda old,new: new + old  # note change of order!
        add_s    = lambda old,new: old + ' ' + new

        # default policy is to keep current keys when there's a conflict
        conflict_solve = dict.fromkeys(self, preserve)

        # the conflict_solve dictionary is given by the user 'inverted': we
        # need a name-function mapping, it comes as a function -> names
        # dict. Make a local copy (b/c we'll make changes), replace user
        # strings for the three builtin policies and invert it.
        if __conflict_solve:
            inv_conflict_solve_user = __conflict_solve.copy()
            for name, func in [('preserve',preserve), ('update',update),
                               ('add',add), ('add_flip',add_flip),
                               ('add_s',add_s)]:
                if name in list(inv_conflict_solve_user.keys()):
                    inv_conflict_solve_user[func] = inv_conflict_solve_user[name]
                    del inv_conflict_solve_user[name]
            conflict_solve.update(self.__dict_invert(inv_conflict_solve_user))
        for key in data_dict:
            if key not in self:
                self[key] = data_dict[key]
            else:
                self[key] = conflict_solve[key](self[key],data_dict[key])


########NEW FILE########
__FILENAME__ = nbbase
"""The basic dict based notebook format.

The Python representation of a notebook is a nested structure of
dictionary subclasses that support attribute access
(.ipstruct.Struct). The functions in this module are merely
helpers to build the structs in the right form.

Authors:

* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import pprint
import uuid

from .ipstruct import Struct

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

# Change this when incrementing the nbformat version
nbformat = 3
nbformat_minor = 0

class NotebookNode(Struct):
    pass


def from_dict(d):
    if isinstance(d, dict):
        newd = NotebookNode()
        for k,v in list(d.items()):
            newd[k] = from_dict(v)
        return newd
    elif isinstance(d, (tuple, list)):
        return [from_dict(i) for i in d]
    else:
        return d


def new_output(output_type=None, output_text=None, output_png=None,
    output_html=None, output_svg=None, output_latex=None, output_json=None,
    output_javascript=None, output_jpeg=None, prompt_number=None,
    ename=None, evalue=None, traceback=None, stream=None, metadata=None):
    """Create a new code cell with input and output"""
    output = NotebookNode()
    if output_type is not None:
        output.output_type = str(output_type)

    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise TypeError("metadata must be dict")
    output.metadata = metadata

    if output_type != 'pyerr':
        if output_text is not None:
            output.text = str(output_text)
        if output_png is not None:
            output.png = bytes(output_png)
        if output_jpeg is not None:
            output.jpeg = bytes(output_jpeg)
        if output_html is not None:
            output.html = str(output_html)
        if output_svg is not None:
            output.svg = str(output_svg)
        if output_latex is not None:
            output.latex = str(output_latex)
        if output_json is not None:
            output.json = str(output_json)
        if output_javascript is not None:
            output.javascript = str(output_javascript)

    if output_type == 'pyout':
        if prompt_number is not None:
            output.prompt_number = int(prompt_number)

    if output_type == 'pyerr':
        if ename is not None:
            output.ename = str(ename)
        if evalue is not None:
            output.evalue = str(evalue)
        if traceback is not None:
            output.traceback = [str(frame) for frame in list(traceback)]

    if output_type == 'stream':
        output.stream = 'stdout' if stream is None else str(stream)
    
    return output


def new_code_cell(input=None, prompt_number=None, outputs=None,
    language='python', collapsed=False, metadata=None):
    """Create a new code cell with input and output"""
    cell = NotebookNode()
    cell.cell_type = 'code'
    if language is not None:
        cell.language = str(language)
    if input is not None:
        cell.input = str(input)
    if prompt_number is not None:
        cell.prompt_number = int(prompt_number)
    if outputs is None:
        cell.outputs = []
    else:
        cell.outputs = outputs
    if collapsed is not None:
        cell.collapsed = bool(collapsed)
    cell.metadata = NotebookNode(metadata or {})

    return cell

def new_text_cell(cell_type, source=None, rendered=None, metadata=None):
    """Create a new text cell."""
    cell = NotebookNode()
    # VERSIONHACK: plaintext -> raw
    # handle never-released plaintext name for raw cells
    if cell_type == 'plaintext':
        cell_type = 'raw'
    if source is not None:
        cell.source = str(source)
    if rendered is not None:
        cell.rendered = str(rendered)
    cell.metadata = NotebookNode(metadata or {})
    cell.cell_type = cell_type
    return cell


def new_heading_cell(source=None, rendered=None, level=1, metadata=None):
    """Create a new section cell with a given integer level."""
    cell = NotebookNode()
    cell.cell_type = 'heading'
    if source is not None:
        cell.source = str(source)
    if rendered is not None:
        cell.rendered = str(rendered)
    cell.level = int(level)
    cell.metadata = NotebookNode(metadata or {})
    return cell


def new_worksheet(name=None, cells=None, metadata=None):
    """Create a worksheet by name with with a list of cells."""
    ws = NotebookNode()
    if name is not None:
        ws.name = str(name)
    if cells is None:
        ws.cells = []
    else:
        ws.cells = list(cells)
    ws.metadata = NotebookNode(metadata or {})
    return ws


def new_notebook(name=None, metadata=None, worksheets=None):
    """Create a notebook by name, id and a list of worksheets."""
    nb = NotebookNode()
    nb.nbformat = nbformat
    nb.nbformat_minor = nbformat_minor
    if worksheets is None:
        nb.worksheets = []
    else:
        nb.worksheets = list(worksheets)
    if metadata is None:
        nb.metadata = new_metadata()
    else:
        nb.metadata = NotebookNode(metadata)
    if name is not None:
        nb.metadata.name = str(name)
    return nb


def new_metadata(name=None, authors=None, license=None, created=None,
    modified=None, gistid=None):
    """Create a new metadata node."""
    metadata = NotebookNode()
    if name is not None:
        metadata.name = str(name)
    if authors is not None:
        metadata.authors = list(authors)
    if created is not None:
        metadata.created = str(created)
    if modified is not None:
        metadata.modified = str(modified)
    if license is not None:
        metadata.license = str(license)
    if gistid is not None:
        metadata.gistid = str(gistid)
    return metadata

def new_author(name=None, email=None, affiliation=None, url=None):
    """Create a new author."""
    author = NotebookNode()
    if name is not None:
        author.name = str(name)
    if email is not None:
        author.email = str(email)
    if affiliation is not None:
        author.affiliation = str(affiliation)
    if url is not None:
        author.url = str(url)
    return author


########NEW FILE########
__FILENAME__ = nbjson
"""Read and write notebooks in JSON format.

Authors:

* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import copy
import json

from .nbbase import from_dict
from .rwbase import (
    NotebookReader, NotebookWriter, restore_bytes, rejoin_lines, split_lines
)

from . import py3compat

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

class BytesEncoder(json.JSONEncoder):
    """A JSON encoder that accepts b64 (and other *ascii*) bytestrings."""
    def default(self, obj):
        if isinstance(obj, bytes):
            return obj.decode('ascii')
        return json.JSONEncoder.default(self, obj)


class JSONReader(NotebookReader):

    def reads(self, s, **kwargs):
        nb = json.loads(s, **kwargs)
        nb = self.to_notebook(nb, **kwargs)
        return nb

    def to_notebook(self, d, **kwargs):
        return restore_bytes(rejoin_lines(from_dict(d)))


class JSONWriter(NotebookWriter):

    def writes(self, nb, **kwargs):
        kwargs['cls'] = BytesEncoder
        kwargs['indent'] = 1
        kwargs['sort_keys'] = True
        kwargs['separators'] = (',',': ')
        if kwargs.pop('split_lines', True):
            nb = split_lines(copy.deepcopy(nb))
        return py3compat.str_to_unicode(json.dumps(nb, **kwargs), 'utf-8')
    

_reader = JSONReader()
_writer = JSONWriter()

reads = _reader.reads
read = _reader.read
to_notebook = _reader.to_notebook
write = _writer.write
writes = _writer.writes


########NEW FILE########
__FILENAME__ = nbpy
"""Read and write notebooks as regular .py files.

Authors:

* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import re
from .rwbase import NotebookReader, NotebookWriter
from .nbbase import (
    new_code_cell, new_text_cell, new_worksheet,
    new_notebook, new_heading_cell, nbformat, nbformat_minor,
)

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

_encoding_declaration_re = re.compile(r"^#.*coding[:=]\s*([-\w.]+)")

class PyReaderError(Exception):
    pass


class PyReader(NotebookReader):

    def reads(self, s, **kwargs):
        return self.to_notebook(s,**kwargs)

    def to_notebook(self, s, **kwargs):
        lines = s.splitlines()
        cells = []
        cell_lines = []
        kwargs = {}
        state = 'codecell'
        for line in lines:
            if line.startswith('# <nbformat>') or _encoding_declaration_re.match(line):
                pass
            elif line.startswith('# <codecell>'):
                cell = self.new_cell(state, cell_lines, **kwargs)
                if cell is not None:
                    cells.append(cell)
                state = 'codecell'
                cell_lines = []
                kwargs = {}
            elif line.startswith('# <htmlcell>'):
                cell = self.new_cell(state, cell_lines, **kwargs)
                if cell is not None:
                    cells.append(cell)
                state = 'htmlcell'
                cell_lines = []
                kwargs = {}
            elif line.startswith('# <markdowncell>'):
                cell = self.new_cell(state, cell_lines, **kwargs)
                if cell is not None:
                    cells.append(cell)
                state = 'markdowncell'
                cell_lines = []
                kwargs = {}
            # VERSIONHACK: plaintext -> raw
            elif line.startswith('# <rawcell>') or line.startswith('# <plaintextcell>'):
                cell = self.new_cell(state, cell_lines, **kwargs)
                if cell is not None:
                    cells.append(cell)
                state = 'rawcell'
                cell_lines = []
                kwargs = {}
            elif line.startswith('# <headingcell'):
                cell = self.new_cell(state, cell_lines, **kwargs)
                if cell is not None:
                    cells.append(cell)
                    cell_lines = []
                m = re.match(r'# <headingcell level=(?P<level>\d)>',line)
                if m is not None:
                    state = 'headingcell'
                    kwargs = {}
                    kwargs['level'] = int(m.group('level'))
                else:
                    state = 'codecell'
                    kwargs = {}
                    cell_lines = []
            else:
                cell_lines.append(line)
        if cell_lines and state == 'codecell':
            cell = self.new_cell(state, cell_lines)
            if cell is not None:
                cells.append(cell)
        ws = new_worksheet(cells=cells)
        nb = new_notebook(worksheets=[ws])
        return nb

    def new_cell(self, state, lines, **kwargs):
        if state == 'codecell':
            input = '\n'.join(lines)
            input = input.strip('\n')
            if input:
                return new_code_cell(input=input)
        elif state == 'htmlcell':
            text = self._remove_comments(lines)
            if text:
                return new_text_cell('html',source=text)
        elif state == 'markdowncell':
            text = self._remove_comments(lines)
            if text:
                return new_text_cell('markdown',source=text)
        elif state == 'rawcell':
            text = self._remove_comments(lines)
            if text:
                return new_text_cell('raw',source=text)
        elif state == 'headingcell':
            text = self._remove_comments(lines)
            level = kwargs.get('level',1)
            if text:
                return new_heading_cell(source=text,level=level)

    def _remove_comments(self, lines):
        new_lines = []
        for line in lines:
            if line.startswith('#'):
                new_lines.append(line[2:])
            else:
                new_lines.append(line)
        text = '\n'.join(new_lines)
        text = text.strip('\n')
        return text

    def split_lines_into_blocks(self, lines):
        if len(lines) == 1:
            yield lines[0]
            raise StopIteration()
        import ast
        source = '\n'.join(lines)
        code = ast.parse(source)
        starts = [x.lineno-1 for x in code.body]
        for i in range(len(starts)-1):
            yield '\n'.join(lines[starts[i]:starts[i+1]]).strip('\n')
        yield '\n'.join(lines[starts[-1]:]).strip('\n')


class PyWriter(NotebookWriter):

    def writes(self, nb, **kwargs):
        lines = ['# -*- coding: utf-8 -*-']
        lines.extend([
            '# <nbformat>%i.%i</nbformat>' % (nbformat, nbformat_minor),
            '',
        ])
        for ws in nb.worksheets:
            for cell in ws.cells:
                if cell.cell_type == 'code':
                    input = cell.get('input')
                    if input is not None:
                        lines.extend(['# <codecell>',''])
                        lines.extend(input.splitlines())
                        lines.append('')
                elif cell.cell_type == 'html':
                    input = cell.get('source')
                    if input is not None:
                        lines.extend(['# <htmlcell>',''])
                        lines.extend(['# ' + line for line in input.splitlines()])
                        lines.append('')
                elif cell.cell_type == 'markdown':
                    input = cell.get('source')
                    if input is not None:
                        lines.extend(['# <markdowncell>',''])
                        lines.extend(['# ' + line for line in input.splitlines()])
                        lines.append('')
                elif cell.cell_type == 'raw':
                    input = cell.get('source')
                    if input is not None:
                        lines.extend(['# <rawcell>',''])
                        lines.extend(['# ' + line for line in input.splitlines()])
                        lines.append('')
                elif cell.cell_type == 'heading':
                    input = cell.get('source')
                    level = cell.get('level',1)
                    if input is not None:
                        lines.extend(['# <headingcell level=%s>' % level,''])
                        lines.extend(['# ' + line for line in input.splitlines()])
                        lines.append('')
        lines.append('')
        return str('\n'.join(lines))


_reader = PyReader()
_writer = PyWriter()

reads = _reader.reads
read = _reader.read
to_notebook = _reader.to_notebook
write = _writer.write
writes = _writer.writes


########NEW FILE########
__FILENAME__ = py3compat
# coding: utf-8
"""Compatibility tricks for Python 3. Mainly to do with unicode."""
import builtins
import functools
import sys
import re
import types

from .encoding import DEFAULT_ENCODING

orig_open = open

def no_code(x, encoding=None):
    return x

def decode(s, encoding=None):
    encoding = encoding or DEFAULT_ENCODING
    return s.decode(encoding, "replace")

def encode(u, encoding=None):
    encoding = encoding or DEFAULT_ENCODING
    return u.encode(encoding, "replace")


def cast_unicode(s, encoding=None):
    if isinstance(s, bytes):
        return decode(s, encoding)
    return s

def cast_bytes(s, encoding=None):
    if not isinstance(s, bytes):
        return encode(s, encoding)
    return s

def _modify_str_or_docstring(str_change_func):
    @functools.wraps(str_change_func)
    def wrapper(func_or_str):
        if isinstance(func_or_str, str):
            func = None
            doc = func_or_str
        else:
            func = func_or_str
            doc = func.__doc__
        
        doc = str_change_func(doc)
        
        if func:
            func.__doc__ = doc
            return func
        return doc
    return wrapper

if sys.version_info[0] >= 3:
    PY3 = True
    
    input = input
    builtin_mod_name = "builtins"
    
    str_to_unicode = no_code
    unicode_to_str = no_code
    str_to_bytes = encode
    bytes_to_str = decode
    cast_bytes_py2 = no_code
    
    string_types = (str,)
    
    def isidentifier(s, dotted=False):
        if dotted:
            return all(isidentifier(a) for a in s.split("."))
        return s.isidentifier()
    
    open = orig_open
    
    MethodType = types.MethodType
    
    def execfile(fname, glob, loc=None):
        loc = loc if (loc is not None) else glob
        with open(fname, 'rb') as f:
            exec(compile(f.read(), fname, 'exec'), glob, loc)
    
    # Refactor print statements in doctests.
    _print_statement_re = re.compile(r"\bprint (?P<expr>.*)$", re.MULTILINE)
    def _print_statement_sub(match):
        expr = match.groups('expr')
        return "print(%s)" % expr
    
    @_modify_str_or_docstring
    def doctest_refactor_print(doc):
        """Refactor 'print x' statements in a doctest to print(x) style. 2to3
        unfortunately doesn't pick up on our doctests.
        
        Can accept a string or a function, so it can be used as a decorator."""
        return _print_statement_re.sub(_print_statement_sub, doc)
    
    # Abstract u'abc' syntax:
    @_modify_str_or_docstring
    def u_format(s):
        """"{u}'abc'" --> "'abc'" (Python 3)
        
        Accepts a string or a function, so it can be used as a decorator."""
        return s.format(u='')

else:
    PY3 = False
    
    input = raw_input
    builtin_mod_name = "__builtin__"
    
    str_to_unicode = decode
    unicode_to_str = encode
    str_to_bytes = no_code
    bytes_to_str = no_code
    cast_bytes_py2 = cast_bytes
    
    string_types = (str, str)
    
    import re
    _name_re = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*$")
    def isidentifier(s, dotted=False):
        if dotted:
            return all(isidentifier(a) for a in s.split("."))
        return bool(_name_re.match(s))
    
    class open(object):
        """Wrapper providing key part of Python 3 open() interface."""
        def __init__(self, fname, mode="r", encoding="utf-8"):
            self.f = orig_open(fname, mode)
            self.enc = encoding
        
        def write(self, s):
            return self.f.write(s.encode(self.enc))
        
        def read(self, size=-1):
            return self.f.read(size).decode(self.enc)
        
        def close(self):
            return self.f.close()
        
        def __enter__(self):
            return self
        
        def __exit__(self, etype, value, traceback):
            self.f.close()
    
    def MethodType(func, instance):
        return types.MethodType(func, instance, type(instance))
    
    # don't override system execfile on 2.x:
    execfile = execfile
    
    def doctest_refactor_print(func_or_str):
        return func_or_str


    # Abstract u'abc' syntax:
    @_modify_str_or_docstring
    def u_format(s):
        """"{u}'abc'" --> "u'abc'" (Python 2)
        
        Accepts a string or a function, so it can be used as a decorator."""
        return s.format(u='u')

    if sys.platform == 'win32':
        def execfile(fname, glob=None, loc=None):
            loc = loc if (loc is not None) else glob
            # The rstrip() is necessary b/c trailing whitespace in files will
            # cause an IndentationError in Python 2.6 (this was fixed in 2.7,
            # but we still support 2.6).  See issue 1027.
            scripttext = builtins.open(fname).read().rstrip() + '\n'
            # compile converts unicode filename to str assuming
            # ascii. Let's do the conversion before calling compile
            if isinstance(fname, str):
                filename = unicode_to_str(fname)
            else:
                filename = fname
            exec(compile(scripttext, filename, 'exec'), glob, loc)
    else:
        def execfile(fname, *where):
            if isinstance(fname, str):
                filename = fname.encode(sys.getfilesystemencoding())
            else:
                filename = fname
            builtins.execfile(filename, *where)

########NEW FILE########
__FILENAME__ = rwbase
"""Base classes and utilities for readers and writers.

Authors:

* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from base64 import encodestring, decodestring
import pprint

from . import py3compat

str_to_bytes = py3compat.str_to_bytes

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

def restore_bytes(nb):
    """Restore bytes of image data from unicode-only formats.
    
    Base64 encoding is handled elsewhere.  Bytes objects in the notebook are
    always b64-encoded. We DO NOT encode/decode around file formats.
    """
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                for output in cell.outputs:
                    if 'png' in output:
                        output.png = str_to_bytes(output.png, 'ascii')
                    if 'jpeg' in output:
                        output.jpeg = str_to_bytes(output.jpeg, 'ascii')
    return nb

# output keys that are likely to have multiline values
_multiline_outputs = ['text', 'html', 'svg', 'latex', 'javascript', 'json']


# FIXME: workaround for old splitlines()
def _join_lines(lines):
    """join lines that have been written by splitlines()
    
    Has logic to protect against `splitlines()`, which
    should have been `splitlines(True)`
    """
    if lines and lines[0].endswith(('\n', '\r')):
        # created by splitlines(True)
        return ''.join(lines)
    else:
        # created by splitlines()
        return '\n'.join(lines)


def rejoin_lines(nb):
    """rejoin multiline text into strings
    
    For reversing effects of ``split_lines(nb)``.
    
    This only rejoins lines that have been split, so if text objects were not split
    they will pass through unchanged.
    
    Used when reading JSON files that may have been passed through split_lines.
    """
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                if 'input' in cell and isinstance(cell.input, list):
                    cell.input = _join_lines(cell.input)
                for output in cell.outputs:
                    for key in _multiline_outputs:
                        item = output.get(key, None)
                        if isinstance(item, list):
                            output[key] = _join_lines(item)
            else: # text, heading cell
                for key in ['source', 'rendered']:
                    item = cell.get(key, None)
                    if isinstance(item, list):
                        cell[key] = _join_lines(item)
    return nb


def split_lines(nb):
    """split likely multiline text into lists of strings
    
    For file output more friendly to line-based VCS. ``rejoin_lines(nb)`` will
    reverse the effects of ``split_lines(nb)``.
    
    Used when writing JSON files.
    """
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                if 'input' in cell and isinstance(cell.input, str):
                    cell.input = cell.input.splitlines(True)
                for output in cell.outputs:
                    for key in _multiline_outputs:
                        item = output.get(key, None)
                        if isinstance(item, str):
                            output[key] = item.splitlines(True)
            else: # text, heading cell
                for key in ['source', 'rendered']:
                    item = cell.get(key, None)
                    if isinstance(item, str):
                        cell[key] = item.splitlines(True)
    return nb

# b64 encode/decode are never actually used, because all bytes objects in
# the notebook are already b64-encoded, and we don't need/want to double-encode

def base64_decode(nb):
    """Restore all bytes objects in the notebook from base64-encoded strings.
    
    Note: This is never used
    """
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                for output in cell.outputs:
                    if 'png' in output:
                        if isinstance(output.png, str):
                            output.png = output.png.encode('ascii')
                        output.png = decodestring(output.png)
                    if 'jpeg' in output:
                        if isinstance(output.jpeg, str):
                            output.jpeg = output.jpeg.encode('ascii')
                        output.jpeg = decodestring(output.jpeg)
    return nb


def base64_encode(nb):
    """Base64 encode all bytes objects in the notebook.
    
    These will be b64-encoded unicode strings
    
    Note: This is never used
    """
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                for output in cell.outputs:
                    if 'png' in output:
                        output.png = encodestring(output.png).decode('ascii')
                    if 'jpeg' in output:
                        output.jpeg = encodestring(output.jpeg).decode('ascii')
    return nb


class NotebookReader(object):
    """A class for reading notebooks."""

    def reads(self, s, **kwargs):
        """Read a notebook from a string."""
        raise NotImplementedError("loads must be implemented in a subclass")

    def read(self, fp, **kwargs):
        """Read a notebook from a file like object"""
        nbs = fp.read()
        if not py3compat.PY3 and not isinstance(nbs, str):
            nbs = py3compat.str_to_unicode(nbs)
        return self.reads(nbs, **kwargs)


class NotebookWriter(object):
    """A class for writing notebooks."""

    def writes(self, nb, **kwargs):
        """Write a notebook to a string."""
        raise NotImplementedError("loads must be implemented in a subclass")

    def write(self, nb, fp, **kwargs):
        """Write a notebook to a file like object"""
        nbs = self.writes(nb,**kwargs)
        if not py3compat.PY3 and not isinstance(nbs, str):
            # this branch is likely only taken for JSON on Python 2
            nbs = py3compat.str_to_unicode(nbs)
        return fp.write(nbs)




########NEW FILE########
__FILENAME__ = websocket3
"""
websocket - WebSocket client library for Python

Copyright (C) 2010 Hiroki Ohtani(liris)

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""


import socket
try:
    import ssl
    HAVE_SSL = True
except ImportError:
    HAVE_SSL = False

from urllib.parse import urlparse
import os
import array
import struct
import uuid
import hashlib
import base64
import threading
import time
import logging
import traceback
import sys

"""
websocket python client.
=========================

This version support only hybi-13.
Please see http://tools.ietf.org/html/rfc6455 for protocol.
"""


# websocket supported version.
VERSION = 13

# closing frame status codes.
STATUS_NORMAL = 1000
STATUS_GOING_AWAY = 1001
STATUS_PROTOCOL_ERROR = 1002
STATUS_UNSUPPORTED_DATA_TYPE = 1003
STATUS_STATUS_NOT_AVAILABLE = 1005
STATUS_ABNORMAL_CLOSED = 1006
STATUS_INVALID_PAYLOAD = 1007
STATUS_POLICY_VIOLATION = 1008
STATUS_MESSAGE_TOO_BIG = 1009
STATUS_INVALID_EXTENSION = 1010
STATUS_UNEXPECTED_CONDITION = 1011
STATUS_TLS_HANDSHAKE_ERROR = 1015

logger = logging.getLogger()


class WebSocketException(Exception):
    """
    websocket exeception class.
    """
    pass


class WebSocketConnectionClosedException(WebSocketException):
    """
    If remote host closed the connection or some network error happened,
    this exception will be raised.
    """
    pass

default_timeout = None
traceEnabled = False


def enableTrace(tracable):
    """
    turn on/off the tracability.

    tracable: boolean value. if set True, tracability is enabled.
    """
    global traceEnabled
    traceEnabled = tracable
    if tracable:
        if not logger.handlers:
            logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)


def setdefaulttimeout(timeout):
    """
    Set the global timeout setting to connect.

    timeout: default socket timeout time. This value is second.
    """
    global default_timeout
    default_timeout = timeout


def getdefaulttimeout():
    """
    Return the global timeout setting(second) to connect.
    """
    return default_timeout


def _parse_url(url):
    """
    parse url and the result is tuple of
    (hostname, port, resource path and the flag of secure mode)

    url: url string.
    """
    if ":" not in url:
        raise ValueError("url is invalid")

    scheme, url = url.split(":", 1)

    parsed = urlparse(url, scheme="http")
    if parsed.hostname:
        hostname = parsed.hostname
    else:
        raise ValueError("hostname is invalid")
    port = 0
    if parsed.port:
        port = parsed.port

    is_secure = False
    if scheme == "ws":
        if not port:
            port = 80
    elif scheme == "wss":
        is_secure = True
        if not port:
            port = 443
    else:
        raise ValueError("scheme %s is invalid" % scheme)

    if parsed.path:
        resource = parsed.path
    else:
        resource = "/"

    if parsed.query:
        resource += "?" + parsed.query

    return (hostname, port, resource, is_secure)


def create_connection(url, timeout=None, **options):
    """
    connect to url and return websocket object.

    Connect to url and return the WebSocket object.
    Passing optional timeout parameter will set the timeout on the socket.
    If no timeout is supplied, the global default timeout setting returned by getdefauttimeout() is used.
    You can customize using 'options'.
    If you set "header" list object, you can set your own custom header.

    >>> conn = create_connection("ws://echo.websocket.org/",
         ...     header=["User-Agent: MyProgram",
         ...             "x-custom: header"])


    timeout: socket timeout time. This value is integer.
             if you set None for this value, it means "use default_timeout value"

    options: current support option is only "header".
             if you set header as dict value, the custom HTTP headers are added.
    """
    sockopt = options.get("sockopt", [])
    sslopt = options.get("sslopt", {})
    websock = WebSocket(sockopt=sockopt, sslopt=sslopt)
    websock.settimeout(timeout if timeout is not None else default_timeout)
    websock.connect(url, **options)
    return websock

_MAX_INTEGER = (1 << 32) -1
_AVAILABLE_KEY_CHARS = list(range(0x21, 0x2f + 1)) + list(range(0x3a, 0x7e + 1))
_MAX_CHAR_BYTE = (1<<8) -1

# ref. Websocket gets an update, and it breaks stuff.
# http://axod.blogspot.com/2010/06/websocket-gets-update-and-it-breaks.html


def _create_sec_websocket_key():
    uid = uuid.uuid4()
    return base64.encodebytes(uid.bytes).strip().decode("utf-8")


_HEADERS_TO_CHECK = {
    "upgrade": "websocket",
    "connection": "upgrade",
    }


class ABNF(object):
    """
    ABNF frame class.
    see http://tools.ietf.org/html/rfc5234
    and http://tools.ietf.org/html/rfc6455#section-5.2
    """

    # operation code values.
    OPCODE_TEXT   = 0x1
    OPCODE_BINARY = 0x2
    OPCODE_CLOSE  = 0x8
    OPCODE_PING   = 0x9
    OPCODE_PONG   = 0xa

    # available operation code value tuple
    OPCODES = (OPCODE_TEXT, OPCODE_BINARY, OPCODE_CLOSE,
                OPCODE_PING, OPCODE_PONG)

    # opcode human readable string
    OPCODE_MAP = {
        OPCODE_TEXT: "text",
        OPCODE_BINARY: "binary",
        OPCODE_CLOSE: "close",
        OPCODE_PING: "ping",
        OPCODE_PONG: "pong"
        }

    # data length threashold.
    LENGTH_7  = 0x7d
    LENGTH_16 = 1 << 16
    LENGTH_63 = 1 << 63

    def __init__(self, fin=0, rsv1=0, rsv2=0, rsv3=0,
                 opcode=OPCODE_TEXT, mask=1, data=""):
        """
        Constructor for ABNF.
        please check RFC for arguments.
        """
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3
        self.opcode = opcode
        self.mask = mask
        self.data = data
        self.get_mask_key = os.urandom

    @staticmethod
    def create_frame(data, opcode):
        """
        create frame to send text, binary and other data.

        data: data to send. This is string value(byte array).
            if opcode is OPCODE_TEXT and this value is uniocde,
            data value is conveted into unicode string, automatically.

        opcode: operation code. please see OPCODE_XXX.
        """
        if opcode == ABNF.OPCODE_TEXT and isinstance(data, str):
            data = data.encode("utf-8")
        # mask must be set if send data from client
        return ABNF(1, 0, 0, 0, opcode, 1, data)

    def format(self):
        """
        format this object to string(byte array) to send data to server.
        """
        if any(x not in (0, 1) for x in [self.fin, self.rsv1, self.rsv2, self.rsv3]):
            raise ValueError("not 0 or 1")
        if self.opcode not in ABNF.OPCODES:
            raise ValueError("Invalid OPCODE")
        length = len(self.data)
        if length >= ABNF.LENGTH_63:
            raise ValueError("data is too long")

        frame_header = []
        frame_header = bytes((self.fin << 7
                           | self.rsv1 << 6 | self.rsv2 << 5 | self.rsv3 << 4
                           | self.opcode,))
        if length < ABNF.LENGTH_7:
            frame_header += bytes((self.mask << 7 | length,))
        elif length < ABNF.LENGTH_16:
            frame_header += bytes((self.mask << 7 | 0x7e,))
            frame_header += struct.pack("!H", length)
        else:
            frame_header += bytes((self.mask << 7 | 0x7f,))
            frame_header += struct.pack("!Q", length)

        if not self.mask:
            return frame_header + self.data
        else:
            mask_key = self.get_mask_key(4)
            return frame_header + self._get_masked(mask_key)

    def _get_masked(self, mask_key):
        s = ABNF.mask(mask_key, self.data)
        return mask_key + s

    @staticmethod
    def mask(mask_key, data):
        """
        mask or unmask data. Just do xor for each byte

        mask_key: 4 byte string(byte).

        data: data to mask/unmask.
        """
        _m = array.array("B", mask_key)
        _d = array.array("B", data)
        for i in range(len(_d)):
            _d[i] ^= _m[i % 4]

        return _d.tobytes()


class WebSocket(object):
    """
    Low level WebSocket interface.
    This class is based on
      The WebSocket protocol draft-hixie-thewebsocketprotocol-76
      http://tools.ietf.org/html/draft-hixie-thewebsocketprotocol-76

    We can connect to the websocket server and send/recieve data.
    The following example is a echo client.

    >>> import websocket
    >>> ws = websocket.WebSocket()
    >>> ws.connect("ws://echo.websocket.org")
    >>> ws.send("Hello, Server")
    >>> ws.recv()
    'Hello, Server'
    >>> ws.close()

    get_mask_key: a callable to produce new mask keys, see the set_mask_key
      function's docstring for more details
    sockopt: values for socket.setsockopt.
        sockopt must be tuple and each element is argument of sock.setscokopt.
    sslopt: dict object for ssl socket option.
    """

    def __init__(self, get_mask_key=None, sockopt=None, sslopt=None):
        """
        Initalize WebSocket object.
        """
        if sockopt is None:
            sockopt = []
        if sslopt is None:
            sslopt = {}
        self.connected = False
        self.sock = socket.socket()
        for opts in sockopt:
            self.sock.setsockopt(*opts)
        self.sslopt = sslopt
        self.get_mask_key = get_mask_key

    def fileno(self):
        return self.sock.fileno()

    def set_mask_key(self, func):
        """
        set function to create musk key. You can custumize mask key generator.
        Mainly, this is for testing purpose.

        func: callable object. the fuct must 1 argument as integer.
              The argument means length of mask key.
              This func must be return string(byte array),
              which length is argument specified.
        """
        self.get_mask_key = func

    def gettimeout(self):
        """
        Get the websocket timeout(second).
        """
        return self.sock.gettimeout()

    def settimeout(self, timeout):
        """
        Set the timeout to the websocket.

        timeout: timeout time(second).
        """
        self.sock.settimeout(timeout)

    timeout = property(gettimeout, settimeout)

    def connect(self, url, **options):
        """
        Connect to url. url is websocket url scheme. ie. ws://host:port/resource
        You can customize using 'options'.
        If you set "header" dict object, you can set your own custom header.

        >>> ws = WebSocket()
        >>> ws.connect("ws://echo.websocket.org/",
                ...     header={"User-Agent: MyProgram",
                ...             "x-custom: header"})

        timeout: socket timeout time. This value is integer.
                 if you set None for this value,
                 it means "use default_timeout value"

        options: current support option is only "header".
                 if you set header as dict value,
                 the custom HTTP headers are added.

        """
        hostname, port, resource, is_secure = _parse_url(url)
        # TODO: we need to support proxy
        self.sock.connect((hostname, port))
        if is_secure:
            if HAVE_SSL:
                if self.sslopt is None:
                    sslopt = {}
                else:
                    sslopt = self.sslopt
                self.sock = ssl.wrap_socket(self.sock, **sslopt)
            else:
                raise WebSocketException("SSL not available.")

        self._handshake(hostname, port, resource, **options)

    def _handshake(self, host, port, resource, **options):
        sock = self.sock
        headers = []
        headers.append("GET %s HTTP/1.1" % resource)
        headers.append("Upgrade: websocket")
        headers.append("Connection: Upgrade")
        if port == 80:
            hostport = host
        else:
            hostport = "%s:%d" % (host, port)
        headers.append("Host: %s" % hostport)

        if "origin" in options:
            headers.append("Origin: %s" % options["origin"])
        else:
            headers.append("Origin: http://%s" % hostport)

        key = _create_sec_websocket_key()
        headers.append("Sec-WebSocket-Key: %s" % key)
        headers.append("Sec-WebSocket-Version: %s" % VERSION)
        if "header" in options:
            headers.extend(options["header"])

        headers.append("")
        headers.append("")

        header_str = "\r\n".join(headers)
        sock.send(bytes(header_str, "utf-8"))
        if traceEnabled:
            logger.debug("--- request header ---")
            logger.debug(header_str)
            logger.debug("-----------------------")

        status, resp_headers = self._read_headers()
        if status != 101:
            self.close()
            raise WebSocketException("Handshake Status %d" % status)

        success = self._validate_header(resp_headers, key)
        if not success:
            self.close()
            raise WebSocketException("Invalid WebSocket Header")

        self.connected = True

    def _validate_header(self, headers, key):
        for k, v in _HEADERS_TO_CHECK.items():
            r = headers.get(k, None)
            if not r:
                return False
            r = r.lower()
            if v != r:
                return False

        result = headers.get("sec-websocket-accept", None)
        if not result:
            return False
        result = result.lower()

        value = key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        digest = hashlib.sha1(bytes(value, "utf-8")).digest()
        hashed = base64.encodebytes(digest).strip().decode("utf-8").lower()
        return hashed == result

    def _read_headers(self):
        status = None
        headers = {}
        if traceEnabled:
            logger.debug("--- response header ---")
        while True:
            line = self._recv_line()
            if line == "\r\n":
                break
            line = line.strip()
            if traceEnabled:
                logger.debug(line)
            if not status:
                status_info = line.split(" ", 2)
                status = int(status_info[1])
            else:
                kv = line.split(":", 1)
                if len(kv) == 2:
                    key, value = kv
                    headers[key.lower()] = value.strip().lower()
                else:
                    raise WebSocketException("Invalid header")

        if traceEnabled:
            logger.debug("-----------------------")

        return status, headers

    def send(self, payload, opcode=ABNF.OPCODE_TEXT):
        """
        Send the data as string.

        payload: Payload must be utf-8 bytes or str,
                  if the opcode is OPCODE_TEXT.
                  Otherwise, it must be byte array

        opcode: operation code to send. Please see OPCODE_XXX.
        """
        if isinstance(payload, str):
            payload = bytes(payload, "utf-8")
        frame = ABNF.create_frame(payload, opcode)
        if self.get_mask_key:
            frame.get_mask_key = self.get_mask_key
        data = frame.format()
        if traceEnabled:
            logger.debug("send: " + repr(data))
        while data:
            l = self.sock.send(data)
            data = data[l:]

    def send_binary(self, payload):
        return self.send(payload, ABNF.OPCODE_BINARY)

    def ping(self, payload=""):
        """
        send ping data.

        payload: data payload to send server.
        """
        self.send(payload, ABNF.OPCODE_PING)

    def pong(self, payload):
        """
        send pong data.

        payload: data payload to send server.
        """
        self.send(payload, ABNF.OPCODE_PONG)

    def recv(self):
        """
        Receive string data(byte array) from the server.

        return value: string(byte array) value.
        """
        opcode, data = self.recv_data()
        if opcode == ABNF.OPCODE_TEXT:
            return data.decode("utf-8")
        return data

    def recv_data(self):
        """
        Recieve data with operation code.

        return  value: tuple of operation code and string(byte array) value.
        """
        while True:
            frame = self.recv_frame()
            if not frame:
                # handle error:
                # 'NoneType' object has no attribute 'opcode'
                raise WebSocketException("Not a valid frame %s" % frame)
            elif frame.opcode in (ABNF.OPCODE_TEXT, ABNF.OPCODE_BINARY):
                return (frame.opcode, frame.data)
            elif frame.opcode == ABNF.OPCODE_CLOSE:
                self.send_close()
                return (frame.opcode, None)
            elif frame.opcode == ABNF.OPCODE_PING:
                self.pong(frame.data)

    def recv_frame(self):
        """
        recieve data as frame from server.

        return value: ABNF frame object.
        """
        header_bytes = self._recv_strict(2)
        if not header_bytes:
            return
        b1 = header_bytes[0]
        fin = b1 >> 7 & 1
        rsv1 = b1 >> 6 & 1
        rsv2 = b1 >> 5 & 1
        rsv3 = b1 >> 4 & 1
        opcode = b1 & 0xf
        b2 = header_bytes[1]
        mask = b2 >> 7 & 1
        length = b2 & 0x7f

        length_data = b""
        if length == 0x7e:
            length_data = self._recv_strict(2)
            length = struct.unpack("!H", length_data)[0]
        elif length == 0x7f:
            length_data = self._recv_strict(8)
            length = struct.unpack("!Q", length_data)[0]

        mask_key = b""
        if mask:
            mask_key = self._recv_strict(4)
        data = self._recv_strict(length)
        if traceEnabled:
            recieved = header_bytes + length_data + mask_key + data
            logger.debug("recv: " + repr(recieved))

        if mask:
            data = ABNF.mask(mask_key, data)

        frame = ABNF(fin, rsv1, rsv2, rsv3, opcode, mask, data)
        return frame

    def send_close(self, status=STATUS_NORMAL, reason=""):
        """
        send close data to the server.

        status: status code to send. see STATUS_XXX.

        reason: the reason to close. This must be string.
        """
        if status < 0 or status >= ABNF.LENGTH_16:
            raise ValueError("code is invalid range")
        self.send(struct.pack('!H', status) + reason, ABNF.OPCODE_CLOSE)

    def close(self, status=STATUS_NORMAL, reason=""):
        """
        Close Websocket object

        status: status code to send. see STATUS_XXX.

        reason: the reason to close. This must be string.
        """
        if self.connected:
            if status < 0 or status >= ABNF.LENGTH_16:
                raise ValueError("code is invalid range")

            try:
                self.send(struct.pack('!H', status) + reason, ABNF.OPCODE_CLOSE)
                timeout = self.sock.gettimeout()
                self.sock.settimeout(3)
                try:
                    frame = self.recv_frame()
                    if logger.isEnabledFor(logging.ERROR):
                        recv_status = struct.unpack("!H", frame.data)[0]
                        if recv_status != STATUS_NORMAL:
                            logger.error("close status: " + repr(recv_status))
                except:
                    pass
                self.sock.settimeout(timeout)
                self.sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
        self._closeInternal()

    def _closeInternal(self):
        self.connected = False
        self.sock.close()

    def _recv(self, bufsize):
        bytes = self.sock.recv(bufsize)
        if not bytes:
            raise WebSocketConnectionClosedException()
        return bytes

    def _recv_strict(self, bufsize):
        remaining = bufsize
        bytes = b""
        while remaining:
            bytes += self._recv(remaining)
            remaining = bufsize - len(bytes)

        return bytes

    def _recv_line(self):
        line = []
        while True:
            c = self._recv(1)
            line.append(c)
            if c == b"\n":
                break
        return b"".join(line).decode("utf-8")


class WebSocketApp(object):
    """
    Higher level of APIs are provided.
    The interface is like JavaScript WebSocket object.
    """
    def __init__(self, url, header=[],
                 on_open=None, on_message=None, on_error=None,
                 on_close=None, keep_running=True, get_mask_key=None):
        """
        url: websocket url.
        header: custom header for websocket handshake.
        on_open: callable object which is called at opening websocket.
          this function has one argument. The arugment is this class object.
        on_message: callbale object which is called when recieved data.
         on_message has 2 arguments.
         The 1st arugment is this class object.
         The passing 2nd arugment is utf-8 string which we get from the server.
       on_error: callable object which is called when we get error.
         on_error has 2 arguments.
         The 1st arugment is this class object.
         The passing 2nd arugment is exception object.
       on_close: callable object which is called when closed the connection.
         this function has one argument. The arugment is this class object.
       keep_running: a boolean flag indicating whether the app's main loop should
         keep running, defaults to True
       get_mask_key: a callable to produce new mask keys, see the WebSocket.set_mask_key's
         docstring for more information
        """
        self.url = url
        self.header = header
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.keep_running = keep_running
        self.get_mask_key = get_mask_key
        self.sock = None

    def send(self, data, opcode=ABNF.OPCODE_TEXT):
        """
        send message.
        data: message to send. If you set opcode to OPCODE_TEXT, data must be utf-8 string or unicode.
        opcode: operation code of data. default is OPCODE_TEXT.
        """
        if self.sock.send(data, opcode) == 0:
            raise WebSocketConnectionClosedException()

    def close(self):
        """
        close websocket connection.
        """
        self.keep_running = False
        self.sock.close()

    def _send_ping(self, interval):
        while self.keep_running:
            time.sleep(interval)
            self.sock.ping()

    def run_forever(self, sockopt=None, sslopt=None, ping_interval=0):
        """
        run event loop for WebSocket framework.
        This loop is infinite loop and is alive during websocket is available.
        sockopt: values for socket.setsockopt.
            sockopt must be tuple and each element is argument of sock.setscokopt.
        sslopt: ssl socket optional dict.
        ping_interval: automatically send "ping" command every specified period(second)
            if set to 0, not send automatically.
        """
        if sockopt is None:
            sockopt = []
        if sslopt is None:
            sslopt = {}
        if self.sock:
            raise WebSocketException("socket is already opened")
        thread = None

        try:
            self.sock = WebSocket(self.get_mask_key, sockopt=sockopt, sslopt=sslopt)
            self.sock.connect(self.url, header=self.header)
            self._callback(self.on_open)

            if ping_interval:
                thread = threading.Thread(target=self._send_ping, args=(ping_interval,))
                thread.setDaemon(True)
                thread.start()

            while self.keep_running:
                data = self.sock.recv()
                if data is None:
                    break
                self._callback(self.on_message, data)
        except Exception as e:
            self._callback(self.on_error, e)
        finally:
            if thread:
                thread.join()
            self.sock.close()
            self._callback(self.on_close)
            self.sock = None

    def _callback(self, callback, *args):
        if callback:
            try:
                callback(self, *args)
            except Exception as e:
                logger.error(e)
                if logger.isEnabledFor(logging.DEBUG):
                    _, _, tb = sys_exc_info()
                    traceback.print_tb(tb)


if __name__ == "__main__":
    enableTrace(True)
    ws = create_connection("ws://echo.websocket.org/")
    print("Sending 'Hello, World'...")
    ws.send("Hello, World")
    print("Sent")
    print("Receiving...")
    result = ws.recv()
    print("Received '%s'" % result)
    ws.close()

########NEW FILE########
__FILENAME__ = ipy_connection
# -*- coding: utf-8 -*-
# Copyright (c) 2013, Maxim Grechkin
# This file is licensed under GNU General Public License version 3
# See COPYING for details.
import json
import uuid

from time import sleep
import threading
import queue

from collections import defaultdict

import re
import sys
import _thread
from .external import nbformat3 as nbformat
from .external.websocket import websocket3 as websocket
from .external.websocket.websocket3 import *
from urllib.request import urlopen, Request, ProxyHandler, build_opener, install_opener, HTTPCookieProcessor
from urllib.parse import urlparse, urlencode
from http.cookiejar import CookieJar

def install_proxy_opener():
    global cookies
    cookies=CookieJar()
    proxy = ProxyHandler({})
    opener = build_opener(proxy, HTTPCookieProcessor(cookies))
    install_opener(opener)

def create_uid():
    return str(uuid.uuid4())

def get_notebooks(baseurl, psswd=None):
    try:
        if psswd!=None:
            target_url=baseurl+'''/login?next=%2F'''
            urlopen(target_url, data=urlencode({'password': psswd}).encode('utf8'))
        target_url = baseurl    +"/notebooks"
        req = urlopen(target_url)
        encoding = req.headers.get_content_charset()
        body = req.readall().decode(encoding)
        if '<input type="password" name="password" id="password_input">' in body:
            return 'psswd'
        data = json.loads(body)
        return data
    except Exception as e:
        print("Error during loading notebook list from ", target_url)
        print(e)
        return None

def create_new_notebook(baseurl):
    try:
        req = urlopen(baseurl + "/new")
        encoding = req.headers.get_content_charset()
        body = req.readall().decode(encoding)
        import re
        match =  re.search("data-notebook-id=(.*)", body)
        nbid = match.groups()[0]
        return nbid
    except :
        raise
    return None

def convert_mime_types(obj, content):
    if not content:
        return obj

    if "text/plain" in content:
        obj.text = content["text/plain"]

    if "text/html" in content:
        obj.html = content["text/html"]

    if "image/svg+xml" in content:
        obj.svg = content["image/svg+xml"]

    if "image/png" in content:
        obj.png = content["image/png"]

    if "image/jpeg" in content:
        obj.jpeg = content["image/jpeg"]

    if "text/latex" in content:
        obj.latex = content["text/latex"]

    if "application/json" in content:
        obj.json = content["application/json"]

    if "application/javascript" in content:
        obj.javascript = content["application/javascript"]

    return obj


class Notebook(object):
    def __init__(self, s):
        self._notebook = nbformat.reads_json(s)
        if len(self._notebook.worksheets) == 0:
             # probably have an empty notebook, create a worksheet
            self._notebook.worksheets.append(nbformat.new_worksheet(cells = [nbformat.new_code_cell(input="")]))
        self._cells = self._notebook.worksheets[0].cells
        self.notebook_view = None

    def __str__(self):
        return nbformat.writes_json(self._notebook)

    def get_cell(self, cell_index):
        return Cell(self._cells[cell_index])

    @property
    def cell_count(self):
        return len(self._cells)

    def create_new_cell(self, position, cell_type):
        if cell_type == "code":
            new_cell = nbformat.new_code_cell(input="")
        elif (cell_type == "markdown") or (cell_type == "raw"):
            new_cell = nbformat.new_text_cell(cell_type, source="")

        if position < 0:
            position = len(self._cells)
        self._cells.insert(position, new_cell)
        return Cell(new_cell)

    def delete_cell(self, cell_index):
        del self._cells[cell_index]

    def name():
        doc = "The name property."

        def fget(self):
            return self._notebook.metadata.name
        def fset(self, value):
            self._notebook.metadata.name = value
        return locals()
    name = property(**name())


MAX_OUTPUT_SIZE = 5000


class Cell(object):
    def __init__(self, obj):
        self._cell = obj
        self.runnig = False
        self.cell_view = None

    @property
    def cell_type(self):
        return self._cell.cell_type

    def source():
        doc = "The source property."

        def fget(self):
            if self.cell_type == "code":
                return "".join(self._cell.input)
            else:
                return "".join(self._cell.source)

        def fset(self, value):
            if self.cell_type == "code":
                self._cell.input = value
            else:
                self._cell.source = value
        return locals()
    source = property(**source())

    @property
    def output(self):
        result = []
        for output in self._cell.outputs:
            if "text" in output:
                result.append(output.text)
            elif "traceback" in output:
                data = "\n".join(output.traceback)
                data = re.sub("\x1b[^m]*m", "", data)  # remove escape characters
                result.append(data)
                if not data.endswith("\n"):
                    result.append("\n")
        result = "".join(result)
        if len(result) > MAX_OUTPUT_SIZE:
            result = result[:MAX_OUTPUT_SIZE] + "..."
        return result

    def on_output(self, msg_type, content):
        output = None
        content = defaultdict(lambda: None, content)  # an easy way to avoid checking all parameters
        if msg_type == "stream":
            output = nbformat.new_output(msg_type, content["data"], stream=content["name"])
        elif msg_type == "pyerr":
            output = nbformat.new_output(msg_type, traceback=content["traceback"], ename=content["ename"], evalue=content["evalue"])
        elif msg_type == "pyout":
            output = nbformat.new_output(msg_type, prompt_number=content["prompt_number"])
            convert_mime_types(output, content["data"])
        elif msg_type == "display_data":
            output = nbformat.new_output(msg_type, prompt_number=content["prompt_number"])
            convert_mime_types(output, content["data"])
        else:
            raise Exception("Unknown msg_type")

        if output:
            self._cell.outputs.append(output)
            if self.cell_view:
                self.cell_view.update_output()

    def on_execute_reply(self, msg_id, content):
        self.running = False
        if 'execution_count' in content:
            self._cell.prompt_number = content['execution_count']
        self.cell_view.on_execute_reply(msg_id, content)

    @property
    def prompt(self):
        if 'prompt_number' in self._cell:
            return str(self._cell.prompt_number)
        else:
            return " "

    def run(self, kernel):
        if self.cell_type != "code":
            return

        self._cell.prompt_number = '*'
        self._cell.outputs = []
        if self.cell_view:
            self.cell_view.update_output()
            self.cell_view.update_prompt_number()

        kernel.run(self.source, output_callback=self.on_output,
                   execute_reply_callback=self.on_execute_reply)


output_msg_types = set(["stream", "display_data", "pyout", "pyerr"])


class Kernel(object):
    def __init__(self, notebook_id, baseurl):
        self.notebook_id = notebook_id
        self.session_id = create_uid()
        self.baseurl = baseurl
        self.shell = None
        self.iopub = None

        self.shell_messages = []
        self.iopub_messages = []
        self.running = False
        self.message_queue = queue.Queue()
        self.message_callbacks = dict()
        self.start_kernel()
        _thread.start_new_thread(self.process_messages, ())
        self.status_callback = lambda x: None
        self.encoding = 'utf-8'

    @property
    def kernel_id(self):
        id = self.get_kernel_id()
        if id is None:
            self.start_kernel()
            return self.get_kernel_id()
        return id

    def get_kernel_id(self):
        notebooks = get_notebooks(self.baseurl)
        for nb in notebooks:
            if nb["notebook_id"] == self.notebook_id:
                return nb["kernel_id"]
        raise Exception("notebook_id not found")

    def start_kernel(self):
        url = self.baseurl + "/kernels?notebook=" + self.notebook_id
        req = urlopen(url, data=b"")  # data="" makes it POST request
        req.read()
        self.create_websockets()

    def restart_kernel(self):
        url = self.baseurl + "/kernels/" + self.kernel_id + "/restart"
        req = urlopen(url, data=b"")
        req.read()
        self.create_websockets()
        self.status_callback("idle")

    def interrupt_kernel(self):
        url = self.baseurl + "/kernels/" + self.kernel_id + "/interrupt"
        req = urlopen(url, data=bytearray(b""))
        req.read()

    def shutdown_kernel(self):
        url = self.baseurl + "/kernels/" + self.kernel_id
        req = Request(url)
        req.add_header("Content-Type", "application/json")
        req.get_method = lambda: "DELETE"
        data = urlopen(req)
        data.read()
        self.status_callback("closed")

    def get_notebook(self):
        req = urlopen(self.notebook_url)
        try:
            return Notebook(req.readall().decode(self.encoding))
        except AttributeError:
            return Notebook(req.read())

    @property
    def notebook_url(self):
        return self.baseurl + "/notebooks/" + self.notebook_id

    def save_notebook(self, notebook):
        request = Request(self.notebook_url, str(notebook).encode(self.encoding))
        request.add_header("Content-Type", "application/json")
        request.get_method = lambda: "PUT"
        data = urlopen(request)
        data.read()

    def on_iopub_msg(self, msg):
        m = json.loads(msg)
        self.iopub_messages.append(m)
        self.message_queue.put(m)

    def on_shell_msg(self, msg):
        m = json.loads(msg)
        self.shell_messages.append(m)
        self.message_queue.put(m)

    def register_callbacks(self, msg_id, output_callback,
                           clear_output_callback=None,
                           execute_reply_callback=None,
                           set_next_input_callback=None):
        callbacks = {"output": output_callback}
        if clear_output_callback:
            callbacks["clear_output"] = clear_output_callback
        if execute_reply_callback:
            callbacks["execute_reply"] = execute_reply_callback
        if set_next_input_callback:
            callbacks["set_next_input"] = set_next_input_callback

        self.message_callbacks[msg_id] = callbacks

    def process_messages(self):
        while True:
            m = self.message_queue.get()
            content = m["content"]
            msg_type = m["header"]["msg_type"]

            if ("parent_header" in m) and ("msg_id" in m["parent_header"]):
                parent_id = m["parent_header"]["msg_id"]
            else:
                parent_id = None

            if msg_type == "status":
                if "execution_state" in content:
                    self.status_callback(content["execution_state"])

            elif parent_id in self.message_callbacks:
                callbacks = self.message_callbacks[parent_id]
                cb = None
                if msg_type in output_msg_types:
                    cb = callbacks["output"]
                elif (msg_type == "clear_output") and ("clear_output" in callbacks):
                    cb = callbacks["clear_output"]
                elif (msg_type == "execute_reply") and ("execute_reply" in callbacks):
                    cb = callbacks["execute_reply"]
                elif (msg_type == "set_next_input") and ("set_next_input" in callbacks):
                    cb = callbacks["set_next_input"]
                elif (msg_type == "complete_reply") and ("complete_reply" in callbacks):
                    cb = callbacks["complete_reply"]

                if cb:
                    cb(msg_type, content)

            self.message_queue.task_done()

    def create_get_output_callback(self, callback):
        def grab_output(msg_type, content):
            if msg_type == "stream":
                callback(content["data"])
            elif msg_type == "pyerr":
                data = "\n".join(content["traceback"])
                data = re.sub("\x1b[^m]*m", "", data)  # remove escape characters
                callback(data)
            elif msg_type == "pyout":
                callback(content["data"]["text/plain"])
            elif msg_type == "display_data":
                callback(content["data"]["text/plain"])

        return grab_output

    def create_websockets(self):
        if self.shell is not None:
            self.shell.close()

        if self.iopub is not None:
            self.iopub.close()

        url = self.baseurl.replace('http', 'ws') + "/kernels/" + self.kernel_id + "/"
        auth=''.join([c.name+'='+c.value for c in cookies])
        self.shell = websocket.WebSocketApp(url=url + "shell",
                                            on_message=lambda ws, msg: self.on_shell_msg(msg),
                                            on_open=lambda ws: ws.send(auth),
                                            on_error=lambda ws, err: print(err))
        self.iopub = websocket.WebSocketApp(url=url + "iopub",
                                            on_message=lambda ws, msg: self.on_iopub_msg(msg),
                                            on_open=lambda ws: ws.send(auth),
                                            on_error=lambda ws, err: print(err))

        _thread.start_new_thread(self.shell.run_forever, ())
        _thread.start_new_thread(self.iopub.run_forever, ())
        sleep(1)
        self.running = True

    def create_message(self, msg_type, content):
        msg = dict(
            header=dict(
                msg_type=msg_type,
                username="username",
                session=self.session_id,
                msg_id=create_uid()),
            content=content,
            parent_header={},
            metadata={})
        return msg

    def send_shell(self, msg):
        if not self.running:
            self.create_websockets()
        self.shell.send(json.dumps(msg))

    def get_completitions(self, line, cursor_pos, text="", timeout=1):
        msg = self.create_message("complete_request",
                                  dict(line=line, cursor_pos=cursor_pos, text=text))
        msg_id = msg["header"]["msg_id"]
        ev = threading.Event()
        matches = []

        def callback(msg_id, content):
            if "matches" in content:
                matches[:] = content["matches"][:]
            ev.set()
        callbacks = {"complete_reply": callback}
        self.message_callbacks[msg_id] = callbacks
        self.send_shell(msg)
        ev.wait(timeout)
        del self.message_callbacks[msg_id]
        return matches

    def run(self, code, output_callback,
            clear_output_callback=None,
            execute_reply_callback=None,
            set_next_input_callback=None):
        msg = self.create_message("execute_request",
                                  dict(code=code, silent=False,
                                  user_variables=[], user_expressions={},
                                  allow_stdin=False))

        msg_id = msg["header"]["msg_id"]
        self.register_callbacks(msg_id,
                                output_callback,
                                clear_output_callback,
                                execute_reply_callback,
                                set_next_input_callback)
        self.send_shell(msg)

########NEW FILE########
__FILENAME__ = ipy_view
# -*- coding: utf-8 -*-
# Copyright (c) 2013, Maxim Grechkin
# This file is licensed under GNU General Public License version 3
# See COPYING for details.
from __future__ import print_function
import sublime
from . import ipy_connection
import re



def create_kernel(baseurl, notebook_id):
    return ipy_connection.Kernel(notebook_id, baseurl)

output_draw_style = sublime.HIDDEN
input_draw_style = sublime.HIDDEN
cell_draw_style = sublime.HIDDEN


class BaseCellView(object):
    def __init__(self, index, view, cell):
        self.index = index
        self.view = view
        self.cell = cell
        self.cell.cell_view = self
        self.buffer_ready = False
        self.owned_regions = ["inb_input"]

    def get_cell_region(self):
        try:
            reg = self.view.get_regions("inb_cells")[self.index]
            return sublime.Region(reg.a+1, reg.b)
        except IndexError:
            return None

    def run(self, kernel, region):
        pass

    def get_region(self, regname):
        cell_reg = self.get_cell_region()
        if cell_reg is None:
            return None
        all_regs = self.view.get_regions(regname)
        for reg in all_regs:
            if cell_reg.contains(reg):
                res = sublime.Region(reg.a+1, reg.b-1)
                return res
        return None

    def get_input_region(self):
        return self.get_region("inb_input")

    def write_to_region(self, edit, regname, text):
        if text is None:
            return
        if text.endswith("\n"):
            text = text[:-1]
        region = self.get_region(regname)
        self.view.set_read_only(False)
        self.view.replace(edit, region, text)

    def select(self, last_line=False):
        input_region = self.get_input_region()
        if input_region is None:
            return

        if last_line:
            pos = self.view.line(input_region.b).a
        else:
            pos = input_region.a

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(pos, pos))
        self.view.show_at_center(pos)

    def setup(self, edit):
        self.buffer_ready = True

    def teardown(self, edit):
        cell_reg = self.get_cell_region()
        for regname in self.owned_regions:
            all_regs = self.view.get_regions(regname)
            all_regs = [reg for reg in all_regs if not cell_reg.contains(reg)]
            self.view.add_regions(regname, all_regs, "source.python", "", input_draw_style)
        self.view.erase(edit, sublime.Region(cell_reg.a, cell_reg.b-1))

    def draw(self, edit):
        if not self.buffer_ready:
            self.setup(edit)

    def get_input_content(self):
        input_region = self.get_input_region()
        if input_region:
            return self.view.substr(input_region)
        else:
            return ""

    def check_R(self):
        pass


class CodeCellView(BaseCellView):
    def __init__(self, nbview, index, view, cell):
        BaseCellView.__init__(self, index, view, cell)
        self.running = False
        self.nbview = nbview
        self.owned_regions.append("inb_output")
        self.old_is_R = self.is_R_cell()
        self.old_prompt_number = -1

    @property
    def prompt(self):
        return self.cell.prompt

    def run(self, kernel):
        if self.running:
            print("Warning")
            print("Cell is already running")
            return

        self.running = True
        code = self.get_code()
        self.cell.source = code
        self.cell.run(kernel)

    def setup(self, edit):
        BaseCellView.setup(self, edit)
        region = self.get_cell_region()
        start = region.a

        view = self.view

        self.view.set_read_only(False)

        start = start + view.insert(edit, start, self.get_input_prompt() % self.prompt)
        end = start + view.insert(edit, start, "\n\n")

        reg = sublime.Region(start, end)
        regs = view.get_regions("inb_input")
        regs.append(reg)
        view.add_regions("inb_input", regs, "source.python", "", input_draw_style)
        self.view.set_read_only(False)

        end = end + view.insert(edit, end, "#/Input[%s]\n\n#Output[%s]" % (self.prompt, self.prompt))

        start = end
        end = start + view.insert(edit, start, "\n\n")

        reg = sublime.Region(start, end)
        regs = view.get_regions("inb_output")
        regs.append(reg)
        view.add_regions("inb_output", regs, "string", "", output_draw_style)
        self.view.set_read_only(False)

        end = end + view.insert(edit, end, "#/Output")

    def update_output(self):
        def run_command():
            self.view.run_command("inb_insert_output", {"cell_index": self.index})
        sublime.set_timeout(run_command, 0)

    def on_execute_reply(self, msg_id, content):
        self.running = False
        self.update_prompt_number()
        if "payload" in content:
            for p in content["payload"]:
                if (p["source"] == "IPython.zmq.page.page") or (p["source"] == "IPython.kernel.zmq.page.page"):
                    self.nbview.on_pager(p["text"])

    def update_prompt_number(self):
        def do_set():
            self.view.run_command('rewrite_prompt_number', {"cell_index": self.index})

        try:
            self.view.run_command('rewrite_prompt_number', {"cell_index": self.index})
        except:
            sublime.set_timeout(do_set, 0)

    def get_input_prompt(self):
        if self.is_R_cell():
            return "#Input-R[%s]"
        else:
            return "#Input[%s]"

    def is_R_cell(self):
        code = self.get_input_content()
        if code == "":
            code = self.cell.source
        return (len(code) >= 3) and (code[:3] == '%%R')

    def check_R(self):
        if self.old_is_R != self.is_R_cell():
            self.update_prompt_number()

    def rewrite_prompt_number(self, edit):
        if (self.prompt == self.old_prompt_number) and (self.old_is_R == self.is_R_cell()):
            return

        self.old_prompt_number = self.prompt
        self.old_is_R = self.is_R_cell()

        inp_reg = self.get_input_region()
        line = self.view.line(inp_reg.begin() - 1)
        self.view.replace(edit, line, self.get_input_prompt() % self.prompt)

        inp_reg = self.get_input_region()
        line = self.view.line(inp_reg.end() + 2)
        self.view.replace(edit, line, "#/Input[%s]" % self.prompt)

        out_reg = self.get_region("inb_output")
        line = self.view.line(out_reg.begin() - 1)
        self.view.replace(edit, line, "#Output[%s]" % self.prompt)



    def output_result(self, edit):
        output = self.cell.output
        output = "\n".join(map(lambda s: " " + s, output.splitlines()))
        self.write_to_region(edit, "inb_output", output)

    def draw(self, edit):
        BaseCellView.draw(self, edit)
        self.write_to_region(edit, "inb_input", self.cell.source)
        self.output_result(edit)

    def get_code(self):
        return self.get_input_content()

    def update_code(self):
        self.cell.source = self.get_code()


class TextCell(BaseCellView):
    def run(self, kernel):
        print("Cannot run Markdown cell")

    def get_cell_title(self):
        if self.cell.cell_type == "markdown":
            return "Markdown"
        elif self.cell.cell_type == "raw":
            return "Raw text"
        elif self.cell.cell_type == "heading":
            return "Heading"
        else:
            print("Unknwon cell type: " + str(self.cell.cell_type))
            return "Unknown"

    def setup(self, edit):
        BaseCellView.setup(self, edit)
        region = self.get_cell_region()
        start = region.a

        view = self.view

        self.view.set_read_only(False)

        start = start + view.insert(edit, start, "#" + self.get_cell_title())
        end = start + view.insert(edit, start, "\n\n")

        reg = sublime.Region(start, end)
        regs = view.get_regions("inb_input")
        regs.append(reg)
        view.add_regions("inb_input", regs, "source.python", "", input_draw_style)
        self.view.set_read_only(False)

        end = end + view.insert(edit, end, "#/" + self.get_cell_title())

    def on_execute_reply(self, msg_id, content):
        raise Exception("Shouldn't get this")

    def draw(self, edit):
        BaseCellView.draw(self, edit)
        self.write_to_region(edit, "inb_input", self.cell.source)

    def get_source(self):
        return self.get_input_content()

    def update_code(self):
        self.cell.source = self.get_source()


class NotebookView(object):
    def __init__(self, view, notebook_id, baseurl):
        self.view = view
        self.baseurl = baseurl
        view.set_scratch(True)
        #view.set_syntax_file("Packages/Python/Python.tmLanguage")
        view.set_syntax_file("Packages/IPython Notebook/SublimeIPythonNotebook.tmLanguage")
        view.settings().set("ipython_notebook", True)
        self.cells = []
        self.notebook_id = notebook_id
        self.kernel = create_kernel(baseurl, notebook_id)
        self.kernel.status_callback = self.on_status
        self.on_status("idle")
        self.notebook = self.kernel.get_notebook()
        self.modified = False
        self.show_modified_status(False)

        self.set_name(self.notebook.name)


    def get_name(self):
        return self.notebook.name

    def set_name(self, new_name):
        self.notebook.name = new_name
        self.view.set_name("IPy Notebook - " + self.notebook.name)

    def get_cell_separator(self):
        return "\n\n"

    def on_sel_modified(self):
        readonly = True
        regset = self.view.get_regions("inb_input")

        first_cell_index = -1
        for s in self.view.sel():
            readonly = True
            for i, reg in enumerate(regset):
                reg = sublime.Region(reg.begin()+1, reg.end()-1)
                if reg.contains(s):
                    if first_cell_index < 0:
                        first_cell_index = i
                    readonly = False
                    break
            if readonly:
                break

        if first_cell_index >= 0:
            self.highlight_cell(regset[first_cell_index])
        else:
            self.view.erase_regions("inb_highlight")

        self.view.set_read_only(readonly)

    def show_modified_status(self, val):
        if val:
            state = "modified"
        else:
            state = "saved"

        def set_status():
            self.view.set_status("NotebookStatus", "notebook: " + state)
        sublime.set_timeout(set_status, 0)

    def set_modified(self, new_val):
        if self.modified != new_val:
            self.show_modified_status(new_val)
        self.modified = new_val

    def on_modified(self):
        self.set_modified(True)

        regset = self.view.get_regions("inb_input")

        for s in self.view.sel():
            for i, reg in enumerate(regset):
                reg = sublime.Region(reg.begin()+1, reg.end()-1)
                if reg.contains(s) and (i < len(self.cells)):
                    self.cells[i].check_R()
                    break

    def highlight_cell(self, input_region):
        reg = self.view.line(input_region.begin()-2)
        reg2 = self.view.line(input_region.end()+2)
        self.view.add_regions("inb_highlight", [reg, reg2], "ipynb.source.highlight", "", sublime.DRAW_EMPTY)

    def on_backspace(self):
        s = self.view.sel()[0]

        regset = self.view.get_regions("inb_input")
        for reg in regset:
            reg = sublime.Region(reg.begin()+2, reg.end())
            if reg.contains(s):
                self.view.run_command("left_delete")
                return
            elif (reg.size() > 2) and (s.begin() == reg.begin() - 1) and (self.view.substr(s.begin()) == "\n"):
                self.view.run_command("left_delete")
                self.view.run_command("move", {"by": "characters", "forward": True})
                return

    def add_cell(self, edit, start=-1):
        view = self.view
        if start < 0:
            start = view.size()

        self.view.set_read_only(False)
        start = start + view.insert(edit, start, self.get_cell_separator())
        end = start + view.insert(edit, start, "\n\n")

        reg = sublime.Region(start, end)
        regs = view.get_regions("inb_cells")
        regs.append(reg)
        view.add_regions("inb_cells", regs, "", "", cell_draw_style)

        return reg

    def insert_cell_field(self, edit, pos=0):
        cell_regions = self.view.get_regions("inb_cells")
        assert len(self.cells) == len(cell_regions)

        if (pos < 0) or (pos > len(self.cells)):
            raise Exception("Wrong position to insert cell field")

        if pos > 0:
            pos = cell_regions[pos-1].b

        self.add_cell(edit, start=pos)

    def run_cell(self, edit, inplace):
        cell_index = self.get_current_cell_index()
        if cell_index < 0:
            return

        cell = self.get_cell_by_index(cell_index)
        if not cell:
            raise Exception("Cell not found")
        if not inplace:
            if cell_index == len(self.cells) - 1:
                self.insert_cell_at_position(edit, cell_index + 1)
        cell.run(self.kernel)
        if not inplace:
            self.move_to_cell(False)

    def get_cell_by_index(self, cell_index):
        res = self.cells[cell_index]
        res.view = self.view
        return res

    def get_current_cell_index(self):
        sel = self.view.sel()
        if len(sel) > 1:
            return -1
        sel = self.view.sel()[0]
        regions = self.view.get_regions("inb_cells")
        return self.find_cell_by_selection(sel, regions)

    def find_cell_by_selection(self, sel, regions):
        for i, reg in enumerate(regions):
            if reg.contains(sel):
                return i
        return -1

    def save_notebook(self):
        self.kernel.save_notebook(self.notebook)
        self.set_modified(False)

    def render_notebook(self, edit):
        self.cells = []
        self.view.erase_regions("inb_cells")
        self.view.erase_regions("inb_input")
        self.view.erase_regions("inb_output")
        for i in range(self.notebook.cell_count):
            self.insert_cell_field(edit, i)
            cell = self.notebook.get_cell(i)
            cell_view = self.create_cell_view(i, self.view, cell)
            self.cells.append(cell_view)

        regions = self.view.get_regions("inb_cells")
        assert len(self.cells) == len(regions)

        for cell in self.cells:
            cell.draw(edit)

        if len(self.cells) > 0:
            self.cells[0].select()

        sublime.set_timeout(lambda : self.set_modified(False), 0)

    def update_notebook_from_buffer(self):
        for cell in self.cells:
            cell.update_code()

    def restart_kernel(self):
        for cell in self.cells:
            if isinstance(cell, CodeCellView):
                cell.running = False
        self.kernel.restart_kernel()

    def shutdown_kernel(self):
        for cell in self.cells:
            if isinstance(cell, CodeCellView):
                cell.running = False
        self.kernel.shutdown_kernel()

    def on_status(self, execution_state):
        def set_status():
            self.view.set_status("ExecutionStatus", "kernel: " + execution_state)
        sublime.set_timeout(set_status, 0)

    def handle_completions(self, view, prefix, locations):
        cell_index = self.get_current_cell_index()
        if cell_index < 0:
            return None
        if not isinstance(self.cells[cell_index], CodeCellView):
            return None
        sel = view.sel()
        if len(sel) > 1:
            return []
        sel = sel[0]
        line = view.substr(view.line(sel))
        row, col = view.rowcol(sel.begin())
        compl = self.kernel.get_completitions(line, col, timeout=0.7)


        if len(compl) > 0:
            def get_last_word(s): # needed for file/directory completion
                if s.endswith("/"):
                    s = s[:-1]
                res = s.split("/")[-1]
                return res

            return ([(s + "\t (IPython)", get_last_word(s)) for s in compl], sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS)
        else:
            return None

    def delete_current_cell(self, edit):
        cell_index = self.get_current_cell_index()
        if cell_index < 0:
            return

        self.update_notebook_from_buffer()
        self.notebook.delete_cell(cell_index)
        self.cells[cell_index].teardown(edit)
        del self.cells[cell_index]
        for cell in self.cells:
            if cell.index >= cell_index:
                cell.index -= 1

        regions = self.view.get_regions("inb_cells")
        reg = regions[cell_index]
        self.view.erase(edit, self.view.full_line(sublime.Region(reg.a, reg.b-1)))
        regions = self.view.get_regions("inb_cells")
        del regions[cell_index]
        self.view.add_regions("inb_cells", regions, "", "", cell_draw_style)
        new_cell_index = cell_index - 1 if cell_index > 0 else 0
        self.cells[new_cell_index].select()

    def insert_cell_below(self, edit):
        cell_index = self.get_current_cell_index()
        if cell_index < 0:
            return

        self.insert_cell_at_position(edit, cell_index + 1)

    def insert_cell_above(self, edit):
        cell_index = self.get_current_cell_index()
        if cell_index < 0:
            return

        self.insert_cell_at_position(edit, cell_index)

    def insert_cell_at_position(self, edit, cell_index):
        self.update_notebook_from_buffer()
        for cell in self.cells:
            if cell.index >= cell_index:
                cell.index += 1

        new_cell = self.notebook.create_new_cell(cell_index, "code")
        new_view = self.create_cell_view(cell_index, self.view, new_cell)
        self.insert_cell_field(edit, cell_index)
        self.cells.insert(cell_index, new_view)
        new_view.draw(edit)
        new_view.select()

    def move_up(self):
        cell_index = self.get_current_cell_index()
        if cell_index < 0:
            return False
        else:
            sel = self.view.sel()[0].begin()
            reg = self.cells[cell_index].get_input_region()
            if self.view.line(reg.begin()) == self.view.line(sel):
                if cell_index > 0:
                    self.cells[cell_index-1].select(last_line=True)
                return True
        return False

    def move_down(self):
        cell_index = self.get_current_cell_index()
        if cell_index < 0:
            return False
        else:
            sel = self.view.sel()[0].begin()
            reg = self.cells[cell_index].get_input_region()
            if self.view.line(reg.end()) == self.view.line(sel):
                if cell_index < len(self.cells) - 1:
                    self.cells[cell_index+1].select()
                return True
        return False

    def move_left(self):
        cell_index = self.get_current_cell_index()
        if cell_index < 0:
            return False
        else:
            sel = self.view.sel()[0].begin()
            reg = self.cells[cell_index].get_input_region()
            if sel == reg.begin():
                return True
        return False

    def move_right(self):
        cell_index = self.get_current_cell_index()
        if cell_index < 0:
            return False
        else:
            sel = self.view.sel()[0].begin()
            reg = self.cells[cell_index].get_input_region()
            if sel == reg.end():
                return True
        return False

    def change_current_cell_type(self, edit, new_type):
        cell_index = self.get_current_cell_index()
        if cell_index < 0:
            return

        if self.cells[cell_index].cell.cell_type == new_type:
            return

        src = self.cells[cell_index].get_input_content()
        self.notebook.delete_cell(cell_index)
        new_cell = self.notebook.create_new_cell(cell_index, new_type)
        new_cell.source = src
        new_view = self.create_cell_view(cell_index, self.view, new_cell)
        self.cells[cell_index].teardown(edit)
        self.cells[cell_index] = new_view
        new_view.draw(edit)
        new_view.select()

    def create_cell_view(self, index, view, cell):
        if cell.cell_type == "code":
            return CodeCellView(self, index, view, cell)
        else:
            return TextCell(index, view, cell)

    def on_pager(self, text):
        text = re.sub("\x1b[^m]*m", "", text)
        def do_run():
            self.view.run_command('set_pager_text', {'text': text})
        try:
            self.view.run_command('set_pager_text', {'text': text})
        except:
            sublime.set_timeout(do_run, 0)


    def move_to_cell(self, up):
        cell_index = self.get_current_cell_index()
        if cell_index < 0:
            return

        if up and cell_index > 0:
            self.cells[cell_index - 1].select(True)
        elif not up and (cell_index < len(self.cells) - 1):
            self.cells[cell_index + 1].select()


class NotebookViewManager(object):
    def __init__(self):
        self.views = {}

    def create_nb_view(self, view, notebook_id, baseurl):
        id = view.id()
        nbview = NotebookView(view, notebook_id, baseurl)
        self.views[id] = nbview
        return nbview

    def get_nb_view(self, view):
        id = view.id()
        if id not in self.views:
            return None
        nbview = self.views[id]
        nbview.view = view
        return nbview

    def on_close(self, view):
        id = view.id()
        if id in self.views:
            del self.views[id]

manager = NotebookViewManager()

########NEW FILE########
__FILENAME__ = subl_ipy_notebook
# -*- coding: utf-8 -*-
# Copyright (c) 2013, Maxim Grechkin
# This file is licensed under GNU General Public License version 3
# See COPYING for details.
import sublime
import sublime_plugin
from . import ipy_view, ipy_connection


manager = ipy_view.manager


class SublimeINListener(sublime_plugin.EventListener):
    def on_selection_modified(self, view):
        nbview = manager.get_nb_view(view)
        if nbview:
            nbview.on_sel_modified()

    def on_modified(self, view):
        nbview = manager.get_nb_view(view)
        if nbview:
            nbview.on_modified()

    def on_close(self, view):
        manager.on_close(view)


def get_last_used_address():
    settings = sublime.load_settings("SublimeIPythonNotebook.sublime-settings")
    lst=settings.get("default_address", [])
    return lst if type(lst)==list else [lst]


def set_last_used_address(value):
    settings = sublime.load_settings("SublimeIPythonNotebook.sublime-settings")
    addresses = get_last_used_address()
    if value in addresses:
        addresses.pop(addresses.index(value))
    settings.set("default_address", [value]+addresses)
    sublime.save_settings("SublimeIPythonNotebook.sublime-settings")

class InbPromptListNotebooksCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.previous_addresses=get_last_used_address()
        if len(self.previous_addresses)==0:
            self.new_server()
            return
        self.previous_addresses += ["New Server"]
        self.window.show_quick_panel(self.previous_addresses, self.on_done)

    def new_server(self):
        self.window.show_input_panel("Notebook host:port : ", "http://127.0.0.1:8888",
                                     self.on_done, None, None)

    def on_done(self, line):
        if line==-1:
            return
        if type(line)==int:
            if line==len(self.previous_addresses)-1:
                self.new_server()
            else:
                self.window.run_command("inb_list_notebooks", {"baseurl": self.previous_addresses[line], "psswd": None})
        else:
            self.window.run_command("inb_list_notebooks", {"baseurl": line, "psswd": None})

class InbPromptPasswordCommand(sublime_plugin.WindowCommand):
    def run(self, baseurl):
        self.baseurl=baseurl
        self.window.show_input_panel("Password: ", '',
                                     self.on_done, None, None)

    def on_done(self, line):
        self.window.run_command("inb_list_notebooks", {"baseurl": self.baseurl, 'psswd': line})


class InbListNotebooksCommand(sublime_plugin.WindowCommand):
    def run(self, baseurl, psswd):
        ipy_connection.install_proxy_opener()

        self.baseurl = baseurl
        nbs = ipy_connection.get_notebooks(baseurl, psswd)
        if nbs=='psswd':
            self.window.run_command("inb_prompt_password", {"baseurl": baseurl})
            return
        if nbs is None:
            print("Cannot get a list of notebooks")
            return
        set_last_used_address(baseurl)
        self.nbs = nbs
        lst = ["0: Create New Notebook\n"]
        for i, nb in enumerate(nbs):
            lst.append(str(i+1) + ":  " + nb["name"] + "\n")

        sublime.set_timeout(lambda: self.window.show_quick_panel(lst, self.on_done), 1)

    def on_done(self, picked):
        if picked == -1:
            return

        view = self.window.new_file()
        if picked > 0:
            manager.create_nb_view(view, self.nbs[picked-1]["notebook_id"], self.baseurl)
        else:
            new_nb_id = ipy_connection.create_new_notebook(self.baseurl)
            if new_nb_id is None:
                return
            manager.create_nb_view(view, new_nb_id, self.baseurl)

        view.run_command("inb_render_notebook")


class SetPagerTextCommand(sublime_plugin.TextCommand):
    """command to set the text in the pop-up pager"""
    def run(self, edit, text):
        pager_view = self.view.window().get_output_panel("help")
        pager_view.insert(edit, 0, text)
        self.view.window().run_command("show_panel", {"panel": "output.help"})


class InbRestartKernelCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if nbview:
            nbview.restart_kernel()


class InbInterruptKernelCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if nbview and nbview.kernel:
            nbview.kernel.interrupt_kernel()


class InbSaveNotebookCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if nbview:
            nbview.update_notebook_from_buffer()
            nbview.save_notebook()

    def description(self):
        return "Save IPython notebook"

class InbShutdownKernelCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if nbview and nbview.kernel:
            nbview.kernel.shutdown_kernel()

class InbBackspaceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if nbview:
            nbview.on_backspace()


class InbClearBufferCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.set_read_only(False)
        self.view.erase(edit, sublime.Region(0, self.view.size()))


class InbRenderNotebookCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if nbview:
            self.view.set_read_only(False)
            self.view.erase(edit, sublime.Region(0, self.view.size()))
            nbview.render_notebook(edit)


class InbInsertOutputCommand(sublime_plugin.TextCommand):
    def run(self, edit, cell_index):
        nbview = manager.get_nb_view(self.view)
        if not nbview:
            raise Exception("Failed to get NBView")

        cell = nbview.get_cell_by_index(cell_index)
        if not cell:
            raise Exception("Failed to get cell")

        cell.output_result(edit)


class InbRunInNotebookCommand(sublime_plugin.TextCommand):
    def run(self, edit, inplace):
        nbview = manager.get_nb_view(self.view)
        if nbview:
            nbview.run_cell(edit, inplace)


class InbDeleteCurrentCellCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if nbview:
            nbview.delete_current_cell(edit)


class InbInsertCellAboveCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if nbview:
            nbview.insert_cell_above(edit)


class InbInsertCellBelowCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if nbview:
            nbview.insert_cell_below(edit)


class InbComplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        nbview = manager.get_nb_view(view)
        if nbview:
            return nbview.handle_completions(view, prefix, locations)


class InbMoveUpCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if not nbview or not nbview.move_up():
            self.view.run_command("move", {"by": "lines", "forward": False})


class InbMoveDownCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if not nbview or not nbview.move_down():
            self.view.run_command("move", {"by": "lines", "forward": True})


class InbMoveLeftCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if not nbview or not nbview.move_left():
            self.view.run_command("move", {"by": "characters", "forward": False})


class InbMoveRightCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if not nbview or not nbview.move_right():
            self.view.run_command("move", {"by": "characters", "forward": True})


class InbOpenAsIpynbCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        nbview = manager.get_nb_view(view)
        if nbview:
            s = str(nbview.notebook)
            new_view = self.window.new_file()
            new_view.run_command('inb_insert_string', {'s': s})
            new_view.set_name(nbview.name + ".ipynb")

class InbInsertStringCommand(sublime_plugin.TextCommand):
    def run(self, edit, s):
        self.view.insert(edit, 0, s)


class InbMoveToCell(sublime_plugin.TextCommand):
    def run(self, edit, up):
        nbview = manager.get_nb_view(self.view)
        if nbview:
            nbview.move_to_cell(up)


class InbChangeCellTypeCommand(sublime_plugin.TextCommand):
    def run(self, edit, new_type):
        nbview = manager.get_nb_view(self.view)
        if nbview:
            nbview.change_current_cell_type(edit, new_type)

class InbRenameNotebookCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nbview = manager.get_nb_view(self.view)
        if nbview:
            self.nbview = nbview
            sublime.active_window().show_input_panel("Notebook name", nbview.get_name(),
                                                            self.on_done, None, None)

    def on_done(self, line):
        self.nbview.set_name(line)


class RewritePromptNumberCommand(sublime_plugin.TextCommand):
    def run(self, edit, cell_index):
        nbview = manager.get_nb_view(self.view)
        if not nbview:
            raise Exception("Failed to get NBView")

        cell = nbview.get_cell_by_index(cell_index)
        if cell:
            cell.rewrite_prompt_number(edit)

########NEW FILE########
