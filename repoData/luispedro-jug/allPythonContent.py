__FILENAME__ = conf
# -*- coding: utf-8 -*-
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os
from jug.jug_version import __version__ as jug_version

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
        'sphinx.ext.autodoc',
        'sphinx.ext.pngmath',
        'sphinx.ext.autosummary',
        'numpydoc',
        'sphinx.ext.intersphinx',
        'sphinx.ext.coverage',
        'sphinx.ext.doctest',
        ]

templates_path = ['.templates']

source_suffix = '.rst'
master_doc = 'index'

project = 'Jug'
copyright = '2008-2013, Luis Pedro Coelho'

# The short X.Y version.
version = jug_version[:3]
# The full version, including alpha/beta/rc tags.
release = jug_version

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be searched
# for source files.
#exclude_dirs = []

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
#html_style = 'default.css'
html_theme = 'nature'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Jugdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'Jug.tex', 'Jug Documentation',
   'Luis Pedro Coelho', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = brute
import itertools
from crypt import decode, letters, isgood, preprocess

ciphertext = file('secret.msg').read()
ciphertext = preprocess(ciphertext)

for p in itertools.product(letters, repeat=5):
    text = decode(ciphertext, p)
    if isgood(text):
        passwd = "".join(map(chr,p))
        print('%s:%s' % (passwd, text))

########NEW FILE########
__FILENAME__ = crypt
import numpy as np

def decode(text, passwd):
    cipher = np.tile(passwd, len(text)/len(passwd))
    text = text ^ cipher
    return "".join(map(chr, text))
encode = decode

def preprocess(ciphertext):
    return np.array(list(map(ord,ciphertext)), np.uint8)

def isgood(text):
    return text.find('Luis Pedro Coelho') >= 0

letters = list(map(ord, 'abcdefghijklmnopqrstuvwxyz'))


if __name__ == '__main__':
    import sys
    text = sys.argv[1]
    passwd = sys.argv[2]
    passwd = list(map(ord, passwd))
    text = np.array(list(map(ord,text)), np.uint8)
    sys.stdout.write(encode(text, passwd))



########NEW FILE########
__FILENAME__ = jugfile
from jug import TaskGenerator
import numpy as np
from itertools import product, chain
from crypt import decode, letters, isgood, preprocess

ciphertext = file('secret.msg').read()
ciphertext = preprocess(ciphertext)

@TaskGenerator
def decrypt(prefix):
    res = []
    for suffix in product(letters, repeat=5-len(prefix)):
        passwd = np.concatenate([prefix, suffix])
        text = decode(ciphertext, passwd)
        if isgood(text):
            passwd = "".join(map(chr, passwd))
            res.append( (passwd, text) )
    return res

@TaskGenerator
def join(partials):
    return list(chain(*partials))

results = []
for p in letters:
    results.append(decrypt([p]))

fullresults = join(results)

########NEW FILE########
__FILENAME__ = printjugresults
import jug
jug.init('jugfile', 'jugdata')
import jugfile
results = jug.task.value(jugfile.fullresults)
for p,t in results:
    print("%s\n\n    Password was '%s'" % (t,p))

########NEW FILE########
__FILENAME__ = primes
from jug import TaskGenerator
from time import sleep

@TaskGenerator
def is_prime(n):
    sleep(1.)
    for j in range(2,n-1):
        if (n % j) == 0:
            return False
    return True

primes100 = list(map(is_prime, range(2,101)))

########NEW FILE########
__FILENAME__ = jugfile
import urllib.request, urllib.error, urllib.parse
from jug import Task
from collections import defaultdict
from time import sleep
import re
from string import lower
from os.path import exists
import json
from os import mkdir

def getdata(title):
    sleep(8)
    # The reason for this cache is to avoid hitting Wikipedia too much in
    # case we are playing around with testing.
    # In a real example, we would *not* have a cache, of course.
    cache = 'text-data/' + title
    if exists(cache):
        return str(file(cache).read(), 'utf-8')

    title = urllib.parse.quote(title)
    url = 'http://en.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&format=json&titles=' + title
    text = urllib.request.urlopen(url).read()
    data = json.loads(text)
    data = list(data['query']['pages'].values())[0]
    text = data['revisions'][0]['*']
    text = re.sub(r'(?x) \[ [^]] *? \]\]', '', text)
    text = re.sub('(?x) {{ [^}]*? }}', '', text)
    text = text.strip()

    try:
        mkdir('text-data')
    except:
        pass
    cache = file(cache, 'w')
    cache.write(text.encode('utf-8'))
    cache.close()
    return text

def isstopword(titlewords, w):
    if not re.match('^\w+$', w): return True
    if w in titlewords: return True
    return False

def countwords(title, document):
    '''
    Takes a file name and returns a wordcount.
    '''
    sleep(4)
    titlewords = list(map(lower, title.split()))
    counts = defaultdict(int)
    for w in document.split():
        w = lower(w)
        if not isstopword(titlewords, w):
            counts[w] += 1
    return dict(counts)

def addcounts(counts):
    '''
    Takes intermediate word counts and puts them together
    '''
    sleep(24)
    allcounts = defaultdict(int)
    for c in counts:
        for k,v in c.items():
            allcounts[k] += v
    return dict(allcounts)

def divergence(global_counts, nr_documents, counts):
    '''
    Takes the global word counts as well as a single count vector
    and returns a set of words *in this document* that are document
    specific.
    '''
    sleep(8)
    specific = []
    for w,n in counts.items():
        if n > global_counts[w]//100:
            specific.append(w)
    specific.sort(key=counts.get)
    specific.reverse()
    return specific

counts = []
for mp in file('MPs.txt'):
    mp = mp.strip()
    document = Task(getdata, mp)
    counts.append(Task(countwords, mp, document))
avgs = Task(addcounts, counts)
results = []
for c in counts:
    results.append(Task(divergence,avgs, len(counts), c))

########NEW FILE########
__FILENAME__ = printresults
import jug
import jug.task

jug.init('jugfile', 'jugdata')
import jugfile

results = jug.task.value(jugfile.results)
for mp,r in zip(file('MPs.txt'), results):
    mp = mp.strip()
    print(mp, ":    ", " ".join(r[:8]))

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
# Copyright (C) 2011-2013, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

'''
This module details all the operations that are necessary to implement a jug
backend.

It can be used as a starting point (template) for writing new backends.
'''

from abc import ABCMeta, abstractmethod

class base_store(object):
    __metaclass__ = ABCMeta
    def __init__(self, name):
        '''
        base_store(name)

        Initialise a backend

        Parameters
        ----------
        name : str
            Internal name to use
        '''

    @abstractmethod
    def dump(self, object, name):
        '''
        store.dump(object, name)

        Saves the object to the backend

        Parameters
        ----------
        object : anything
        name : str
            Key to use
        '''

    @abstractmethod
    def list(self):
        '''
        for key in store.list():
            ...

        Iterates over all the keys in the store
        '''


    @abstractmethod
    def can_load(self, name):
        '''
        can = store.can_load(name)

        Parameters
        ----------
        name : str
            Key to use

        Returns
        -------
        can : bool
        '''

    @abstractmethod
    def load(self, name):
        '''
        obj = store.load(name)

        Loads one object from the store.

        Parameters
        ----------
        name : str
            Key to use

        Returns
        -------
        obj : any
            The object that was saved under ``name``
        '''

    @abstractmethod
    def remove(self, name):
        '''
        was_removed = store.remove(name)

        Remove the entry associated with ``name``.

        Returns whether any entry was actually removed.

        Parameters
        ----------
        name : str
            Key

        Returns
        -------
        was_removed : bool
            Whether the key was present
        '''

    @abstractmethod
    def cleanup(self, active):
        '''
        nr_removed = store.cleanup(active)

        Implement 'cleanup' command

        Parameters
        ----------
        active : sequence
            files *not to remove*

        Returns
        -------
        nr_removed : integer
            number of removed files
        '''


    @abstractmethod
    def remove_locks(self):
        '''
        removed = store.remove_locks()

        Remove all locks

        Returns
        -------
        removed : int
            Number of locks removed
        '''


    @abstractmethod
    def getlock(self, name):
        '''
        lock = store.getlock(name)

        Retrieve a lock object associated with ``name``.

        Parameters
        ----------
        name : str
            Key

        Returns
        -------
        lock : Lock object
            This should obey the Lock Interface

        See Also
        --------
        base_lock : Generic lock
        '''

    @abstractmethod
    def close(self):
        '''
        store.close()

        Close the connection.

        Mayb be a no-op.
        '''

    @staticmethod
    def remove_store(jugdir):
        '''
        store_class.remove_store(jugdir)

        Removes all that is associated with the store identified by ``jugdir``.

        For example, it might remove files on disk, drop tables on the
        database, &c
        '''

    def metadata(self, t):
        return None


class base_lock(object):
    __metaclass__ = ABCMeta
    '''

    Functions:
    ----------

    - get(): acquire the lock
    - release(): release the lock
    - is_locked(): check lock state
    '''

    def __init__(self):
        '''
        A lock class does not need to have an __init__ method with any specific
        signature. It is only to be used from *within* store.lock().
        '''

    @abstractmethod
    def get(self):
        '''
        locked = lock.get()

        Try to atomically create a lock

        Parameters
        ----------
        None

        Returns
        -------
        locked : bool
            Whether the lock was created
        '''

    @abstractmethod
    def release(self):
        '''
        lock.release()

        Releases lock
        '''

    @abstractmethod
    def is_locked(self):
        '''
        locked = lock.is_locked()

        Returns whether a lock exists for name. Note that the answer can
        be invalid by the time this function returns. Only by trying to
        acquire the lock can you avoid race-conditions. See the get() function.

        This function is provided only because it might be possible to have a
        fast check before calling the expensive locking operation.

        Returns
        -------
        locked : boolean
        '''


########NEW FILE########
__FILENAME__ = dict_store
#-*- coding: utf-8 -*-
# Copyright (C) 2009-2013, Luis Pedro Coelho <luis@luispedro.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

'''
dict_store: an in-memory dictionary.

Does not support multiple processes!
'''

from six.moves import cPickle as pickle
from collections import defaultdict

from .base import base_store
import six

def _resultname(name):
    return six.b('result:')+name

def _lockname(name):
    return six.b('lock:')+name


class dict_store(base_store):
    def __init__(self, backend=None):
        '''
        dict_store(backend=None)

        Parameters
        ----------
        backend : str, optional
                  filename to load/save to
        '''
        if backend is not None:
            try:
                self.store = pickle.load(open(backend))
            except IOError:
                self.store = {}
        else:
            self.store = {}
        self.backend = backend
        self.counts = defaultdict(int)

    def dump(self, object, name):
        '''
        self.dump(object, name)
        '''
        self.store[_resultname(name)] = pickle.dumps(object)
        self.counts['dump:{0}'.format(name)] += 1


    def can_load(self, name):
        '''
        can = can_load(name)
        '''
        self.counts['exists:{0}'.format(name)] += 1
        return _resultname(name) in self.store


    def load(self, name):
        '''
        obj = load(name)

        Loads the objects. Equivalent to pickle.load(), but a bit smarter at times.
        '''
        self.counts['load:{0}'.format(name)] += 1
        return pickle.loads(self.store[_resultname(name)])


    def remove(self, name):
        '''
        was_removed = remove(name)

        Remove the entry associated with name.

        Returns whether any entry was actually removed.
        '''
        self.counts['del:{0}'.format(name)] += 1
        if self.can_load(name):
            self.counts['true-del:{0}'.format(name)] += 1
            del self.store[_resultname(name)]


    def cleanup(self, active):
        '''
        cleanup()

        Implement 'cleanup' command
        '''
        existing = set(self.store.keys())
        for act in active:
            try:
                existing.remove(_resultname(act))
            except KeyError:
                pass
        for superflous in existing:
            del self.store[superflous]

    def remove_locks(self):
        '''
        removed = store.remove_locks()

        Remove all locks

        Returns
        -------
        removed : int
            Number of locks removed
        '''
        removed = 0
                # we need a copy of the keys because we change it inside
                # iteration:
        for k in list(self.store.keys()):
            if k.startswith(six.b('lock:')):
                del self.store[k]
                removed += 1
        return removed

    def list(self):
        '''
        for key in store.list():
            ...

        Iterates over all the keys in the store
        '''
        for k in self.store.keys():
            if k.startswith(six.b('result:')):
                yield k[len('result:'):]

    def listlocks(self):
        '''
        for key in store.listlocks():
            ...

        Iterates over all the keys in the store
        '''
        for k in self.store.keys():
            if k.startswith(six.b('lock:')):
                yield k[len('lock:'):]


    def getlock(self, name):
        return dict_lock(self.store, self.counts, name)

    def close(self):
        if self.backend is not None:
            pickle.dump(self.store, file(self.backend, 'w'))
            self.backend = None
    __del__ = close


_NOT_LOCKED, _LOCKED = 0,1
class dict_lock(object):
    '''
    dict_lock

    Functions:
    ----------

    get()
        acquire the lock
    release()
        release the lock
    is_locked()
        check lock state
    '''

    def __init__(self, store, counts, name):
        self.name = _lockname(name)
        self.store = store
        self.counts = counts

    def get(self):
        '''
        lock.get()
        '''

        self.counts[six.b('lock:') + self.name] += 1

        previous = self.store.get(self.name, _NOT_LOCKED)
        self.store[self.name] = _LOCKED
        return previous == _NOT_LOCKED


    def release(self):
        '''
        lock.release()

        Removes lock
        '''
        self.counts[six.b('unlock:') + self.name] += 1
        del self.store[self.name]

    def is_locked(self):
        '''
        locked = lock.is_locked()
        '''
        self.counts[six.b('islock:') + self.name] += 1
        return (self.store.get(self.name, _NOT_LOCKED) == _LOCKED)

# vim: set ts=4 sts=4 sw=4 expandtab smartindent:

########NEW FILE########
__FILENAME__ = encode
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2014, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.


from six.moves import cPickle as pickle
from six import BytesIO
import six
import zlib

__all__ = ['encode', 'decode', 'encode_to', 'decode_from']

def encode(object):
    '''
    s = encode(object)

    Return a string (byte-array) representation of object.

    Parameters
    ----------
      object : Any thing that is pickle()able

    Returns
    -------
      s : string (byte array).

    See
    ---
      `decode`
    '''
    output = BytesIO()
    encode_to(object, output)
    return output.getvalue()

def encode_to(object, stream):
    '''
    encode_to(object, stream)

    Encodes the object into the stream ``stream``

    Parameters
    ----------
    object : Any object
    stream : file-like object
    '''
    if object is None:
        return
    prefix = six.b('P')
    write = pickle.dump
    try:
        import numpy as np
        if type(object) == np.ndarray:
            prefix = six.b('N')
            write = (lambda f,a: np.save(a,f))
    except ImportError:
        pass
    stream = compress_stream(stream)
    stream.write(prefix)
    write(object, stream)
    stream.flush()

class compress_stream(object):
    def __init__(self, stream):
        self.stream = stream
        self.C = zlib.compressobj()

    def write(self, s):
        self.stream.write(self.C.compress(s))

    def flush(self):
        self.stream.write(self.C.flush())
        self.stream.flush()

class decompress_stream(object):
    def __init__(self, stream, block=8192):
        self.stream = stream
        self.D = zlib.decompressobj()
        self.block = block
        self.lastread = six.b('')
        self.queue = six.b('')

    def read(self, nbytes):
        res = six.b('')
        if self.queue:
            if len(self.queue) >= nbytes:
                res = self.queue[:nbytes]
                self.queue = self.queue[nbytes:]
                return res
            res = self.queue
            self.queue = b''

        if self.D.unconsumed_tail:
            res += self.D.decompress(self.D.unconsumed_tail, nbytes - len(res))
        while len(res) < nbytes:
            buf = self.stream.read(self.block)
            if not buf:
                res += self.D.flush()
                break
            res += self.D.decompress(buf, nbytes - len(res))
        self.lastread = res
        return res

    def seek(self, offset, whence):
        if whence != 1:
            raise NotImplementedError
        while offset > 0:
            nbytes = min(offset, self.block)
            self.read(nbytes)
            offset -= nbytes
        if offset < 0:
            if offset > len(self.lastread):
                raise ValueError('seek too far')
            skip = len(self.lastread) + offset
            self.queue = self.lastread[skip:]

    def readline(self):
        import six
        qi = self.queue.find(six.b('\n'))
        if qi >= 0:
            qi += 1
            res = self.queue[:qi]
            self.queue = self.queue[qi:]
            return res
        line = six.b('')
        while True:
            block = self.read(self.block)
            if not block:
                return line
            ln = block.find(six.b('\n'))
            if ln == -1:
                line += block
            else:
                ln += 1
                line += block[:ln]
                self.seek(ln-len(block), 1)
                return line
        return line

def decode(s):
    '''
    object = decode(s)

    Reverses `encode`.

    Parameters
    ----------
      s : a string representation of the object.

    Returns
    -------
      object : the object
    '''
    return decode_from(BytesIO(s))

def decode_from(stream):
    '''
    object = decode_from(stream)

    Decodes the object from the stream ``stream``

    Parameters
    ----------
    stream : file-like object

    Returns
    -------
    object : decoded object
    '''
    stream = decompress_stream(stream)
    prefix = stream.read(1)
    if not prefix:
        return None
    elif prefix == six.b('P'):
        return pickle.load(stream)
    elif prefix == six.b('N'):
        import numpy as np
        return np.load(stream)
    else:
        raise IOError("jug.backend.decode_from: unknown prefix '%s'" % prefix)

########NEW FILE########
__FILENAME__ = file_store
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2013, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

'''
file_store : file-system based data store & locks.
'''


import os
from os import path, mkdir
from os.path import dirname, exists
import errno
import tempfile
import shutil

from .base import base_store
from jug.backends.encode import encode_to, decode_from

def create_directories(dname):
    '''
    create_directories(dname)

    Recursively create directories.
    '''
    if dname.endswith('/'): dname = dname[:-1]
    head, tail = path.split(dname)
    if path.exists(dname): return
    if head: create_directories(head)
    try:
        mkdir(dname)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


class file_store(base_store):
    def __init__(self, dname):
        '''
        file_store(dname)

        Recursively create directories.
        '''
        if dname.endswith('/'): dname = dname[:-1]
        self.jugdir = dname

    def create(self):
        '''
        Recursively create directories.
        '''
        create_directories(self.jugdir)
        create_directories(self.tempdir())

    def _maybe_create(self):
        '''
        Calls self.create() the first time it is called; then becomes a no-op.
        '''
        self.create()
        self._maybe_create = (lambda : None)

    def tempdir(self):
        return path.join(self.jugdir, 'tempfiles')

    def _getfname(self, name):
        import six
        name = six.text_type(name)
        return path.join(self.jugdir, name[:2], name[2:])


    def dump(self, object, name):
        '''
        store.dump(object, name)

        Performs the same as

        pickle.dump(object, open(name,'w'))

        but does it in a way that is guaranteed to be atomic even over NFS.
        '''
        name = self._getfname(name)
        create_directories(dirname(name))
        self._maybe_create()
        fd, fname = tempfile.mkstemp('.jugtmp', 'jugtemp', self.tempdir())
        output = os.fdopen(fd, 'wb')
        try:
            import numpy as np
            if type(object) == np.ndarray:
                np.lib.format.write_array(output, object)
                output.flush()
                os.fsync(output.fileno())
                output.close()
                os.rename(fname, name)
                return
        except ImportError:
            pass
        except OSError:
            pass
        except ValueError:
            pass

        encode_to(object, output)
        output.flush()
        os.fsync(output.fileno())
        output.close()

        # Rename is atomic even over NFS.
        os.rename(fname, name)

    def list(self):
        '''
        keys = store.list()

        Returns a list of all the keys in the store
        '''
        if not exists(self.jugdir):
            return []

        keys = []
        for d in os.listdir(self.jugdir):
            if len(d) == 2:
                for f in os.listdir(self.jugdir + '/' + d):
                    keys.append(d+f)
        return keys


    def listlocks(self):
        '''
        keys = store.listlocks()

        Returns a list of all the locks in the store

        This is an unsafe function as the results may be outdated by the time
        the function returns.
        '''
        if not exists(self.jugdir + '/locks'):
            return []

        keys = []
        for k in os.listdir(self.jugdir + '/locks'):
            keys.append(k[:-len('.lock')])
        return keys


    def can_load(self, name):
        '''
        can = store.can_load(name)
        '''
        fname = self._getfname(name)
        return exists(fname)


    def load(self, name):
        '''
        obj = store.load(name)

        Loads the objects. Equivalent to pickle.load(), but a bit smarter at
        times.

        Parameters
        ----------
        name : str
            Key to use

        Returns
        -------
        obj : any
            The object that was saved under ``name``
        '''
        fname = self._getfname(name)
        input = open(fname, 'rb')
        try:
            import numpy as np
            return np.lib.format.read_array(input)
        except ValueError:
            input.seek(0)
        except ImportError:
            pass
        return decode_from(input)

    def remove(self, name):
        '''
        was_removed = store.remove(name)

        Remove the entry associated with name.

        Returns whether any entry was actually removed.
        '''
        try:
            fname = self._getfname(name)
            os.unlink(fname)
            return True
        except OSError:
            return False

    def cleanup(self, active):
        '''
        nr_removed = store.cleanup(active)

        Implement 'cleanup' command

        Parameters
        ----------
        active : sequence
            files *not to remove*

        Returns
        -------
        nr_removed : integer
            number of removed files
        '''
        active = frozenset(self._getfname(t.hash()) for t in active)
        removed = 0
        for dir,_,fs in os.walk(self.jugdir):
            for f in fs:
                f = path.join(dir, f)
                if f not in active:
                    os.unlink(f)
                    removed += 1
        return removed

    def remove_locks(self):
        '''
        removed = store.remove_locks()

        Remove all locks

        Returns
        -------
        removed : int
            Number of locks removed
        '''

        lockdir = path.join(self.jugdir, 'locks')
        if not exists(lockdir): return 0

        removed = 0
        for f in os.listdir(lockdir):
            os.unlink(path.join(lockdir, f))
            removed += 1
        return removed

    def getlock(self, name):
        '''
        lock = store.getlock(name)

        Retrieve a lock object associated with ``name``.

        Parameters
        ----------
        name : str
            Key

        Returns
        -------
        lock : Lock object
            This is a file_lock object
        '''
        self._maybe_create()
        return file_based_lock(self.jugdir, name)

    def close(self):
        '''
        store.close()

        Has no effect on file based stores.
        '''
        pass

    def metadata(self, t):
        '''
        meta = store.metadata(t)

        Retrieves information on the state of the computation

        Parameters
        ----------
        t : Task
            A Task object

        Returns
        -------
        meta : dict
            Dictionary describing the state of the computation
        '''
        from os import stat, path
        from time import ctime
        fname = self._getfname(t.hash())
        if path.exists(fname):
            st = stat(fname)
            return {
                'computed': True,
                'completed': ctime(st.st_mtime),
            }
        return {
                'computed': False
        }


    @staticmethod
    def remove_store(jugdir):
        '''
        file_store.remove_store(jugdir)

        Removes from disk all the files associated with this jugdir.
        '''
        shutil.rmtree(jugdir)


class file_based_lock(object):
    '''
    file_based_lock: File-system based locks

    Functions:
    ----------

    - get(): acquire the lock
    - release(): release the lock
    - is_locked(): check lock state
    '''

    def __init__(self, jugdir, name):
        self.fullname = path.join(jugdir, 'locks', '{0}.lock'.format(name))

    def get(self):
        '''
        lock.get()

        Create a lock for name in an NFS compatible way.

        Parameters
        ----------
        None

        Returns
        -------
        locked : bool
            Whether the lock was created
        '''
        if exists(self.fullname): return False
        create_directories(path.dirname(self.fullname))
        try:
            import socket
            fd = os.open(self.fullname,os.O_RDWR|os.O_CREAT|os.O_EXCL)
            F = os.fdopen(fd,'w')
            F.write('%s on %s\n' % (os.getpid(), socket.gethostname()))
            F.close()
            return True
        except OSError:
            return False

    def release(self):
        '''
        lock.release()

        Removes lock
        '''
        try:
            os.unlink(self.fullname)
        except OSError:
            pass

    def is_locked(self):
        '''
        locked = lock.is_locked()

        Returns whether a lock exists for name. Note that the answer can
        be invalid by the time this function returns. Only by trying to
        acquire the lock can you avoid race-conditions. See the get() function.
        '''
        return path.exists(self.fullname)


########NEW FILE########
__FILENAME__ = memoize_store
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2011, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

'''
memoize_store: a wrapper that never repeats a lookup.
'''


class memoize_store(object):
    def __init__(self, base, list_base=False):
        '''
        '''
        self.base = base
        self.cache = {}
        self.keys = None
        self.locks = None
        if list_base and hasattr(base, 'list'):
            self.keys = set(base.list())
        if list_base and hasattr(base, 'listlocks'):
            self.locks = set(base.listlocks())

    def dump(self, object, outname):
        '''
        dump(outname, object)
        '''
        raise NotImplementedError


    def can_load(self, name):
        '''
        can = can_load(name)
        '''
        if self.keys is not None:
            return name in self.keys
        if ('can-load', name) not in self.cache:
            self.cache['can-load', name] = self.base.can_load(name)
        return self.cache['can-load',name]


    def load(self, name):
        '''
        obj = load(name)

        Loads the objects. Equivalent to pickle.load(), but a bit smarter at times.
        '''
        raise NotImplementedError


    def remove(self, name):
        '''
        was_removed = remove(name)

        Remove the entry associated with name.

        Returns whether any entry was actually removed.
        '''
        raise NotImplementedError


    def cleanup(self, active):
        '''
        cleanup()

        Implement 'cleanup' command
        '''
        raise NotImplementedError


    def getlock(self, name):
        return cache_lock(self.base, name, self.locks)


    def close(self):
        pass


_UNKNOWN, _NOT_LOCKED, _LOCKED = -1,False,True
class cache_lock(object):
    '''
    cache_lock

    Functions:
    ----------
    get(): acquire the lock
    release(): release the lock
    is_locked(): check lock state
    '''

    def __init__(self, base, name, locks):
        self.base = base.getlock(name)
        self.status = _UNKNOWN
        if locks is not None:
            self.status = (_LOCKED if (name in locks) else _NOT_LOCKED)

    def get(self):
        '''
        lock.get()
        '''
        raise NotImplementedError


    def release(self):
        '''
        lock.release()

        Removes lock
        '''
        raise NotImplementedError

    def is_locked(self):
        '''
        locked = lock.is_locked()
        '''
        if self.status == _UNKNOWN:
            self.status = (_LOCKED if self.base.is_locked() else _NOT_LOCKED)
        return self.status


########NEW FILE########
__FILENAME__ = redis_store
#-*- coding: utf-8 -*-
# Copyright (C) 2009-2011, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

'''
redis_store: store based on a redis backend
'''


import re
import logging
from base64 import b64encode, b64decode

from jug.backends.encode import encode, decode
from .base import base_store, base_lock


try:
    import redis
    redis_functional = True
except ImportError:
    redis = None
    redis_functional = False

def _resultname(name):
    return 'result:{0}'.format(name).encode('utf-8')

def _lockname(name):
    return 'lock:{0}'.format(name).encode('utf-8')

_LOCKED = 1

_redis_urlpat = re.compile(r'redis://(?P<host>[A-Za-z0-9\.\-]+)(\:(?P<port>[0-9]+))?/')


class redis_store(base_store):
    def __init__(self, url):
        '''
        '''
        if redis is None:
            raise IOError('jug.redis_store: redis module is not found!')
        redis_params = {}
        match = _redis_urlpat.match(url)
        if match:
            redis_params = match.groupdict()
            if redis_params['port'] == None:
                del redis_params['port']
            else:
                redis_params['port'] = int( redis_params['port'] )
        logging.info('connecting to %s' % redis_params)

        self.redis = redis.Redis(**redis_params)


    def dump(self, object, name):
        '''
        dump(object, name)
        '''
        s = encode(object)
        if s:
            s = b64encode(s)
        self.redis.set(_resultname(name), s)


    def can_load(self, name):
        '''
        can = can_load(name)
        '''
        return self.redis.exists(_resultname(name))


    def load(self, name):
        '''
        obj = load(name)

        Loads the object identified by `name`.
        '''
        s = self.redis.get(_resultname(name))
        if s:
            s = b64decode(s)
        return decode(s)


    def remove(self, name):
        '''
        was_removed = remove(name)

        Remove the entry associated with name.

        Returns whether any entry was actually removed.
        '''
        return self.redis.delete(_resultname(name))


    def cleanup(self, active):
        '''
        cleanup()

        Implement 'cleanup' command
        '''
        existing = list(self.list())
        for act in active:
            try:
                existing.remove(_resultname(act))
            except KeyError:
                pass
        for superflous in existing:
            self.redis.delete(_resultname(superflous))

    def remove_locks(self):
        locks = self.redis.keys('lock:*')
        for lk in locks:
            self.redis.delete(lk)
        return len(locks)

    def list(self):
        existing = self.redis.keys('result:*')
        for ex in existing:
            yield ex[len('result:'):]

    def listlocks(self):
        locks = self.redis.keys('lock:*')
        for lk in locks:
            yield lk[len('lock:')]


    def getlock(self, name):
        return redis_lock(self.redis, name)


    def close(self):
        # It seems some versions of the protocol are implemented differently
        # and do not have the ``disconnect`` method
        try:
            self.redis.disconnect()
        except:
            pass



class redis_lock(base_lock):
    '''
    redis_lock

    Functions:
    ----------

        * get(): acquire the lock
        * release(): release the lock
        * is_locked(): check lock state
    '''

    def __init__(self, redis, name):
        self.name = _lockname(name)
        self.redis = redis


    def get(self):
        '''
        lock.get()
        '''
        previous = self.redis.getset(self.name, _LOCKED)
        return (previous is None)


    def release(self):
        '''
        lock.release()

        Removes lock
        '''
        self.redis.delete(self.name)


    def is_locked(self):
        '''
        locked = lock.is_locked()
        '''
        status = self.redis.get(self.name)
        return status is not None and status == _LOCKED


########NEW FILE########
__FILENAME__ = select
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2010, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.


from . import redis_store
from . import file_store
from .dict_store import dict_store

def select(jugdir):
    '''
    store = select(jugdir)

    Returns a store object appropriate for `jugdir`

    Parameters
    ----------
      jugdir : string
            representation of jugdir.
            Alternatively, if not a string, a data store

    Returns
    -------
      store : A jug data store
    '''
    if type(jugdir) != str:
        return jugdir
    if jugdir.startswith('redis:'):
       return redis_store.redis_store(jugdir)
    if jugdir == 'dict_store':
        return dict_store()
    if jugdir.startswith('dict_store:'):
        return dict_store(jugdir[len('dict_store:'):])
    return file_store.file_store(jugdir)


########NEW FILE########
__FILENAME__ = barrier
# -*- coding: utf-8 -*-
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
# Copyright (C) 2010-2012, Luis Pedro Coelho <luis@luispedro.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

class BarrierError(Exception):
    '''
    Used to represent a barrier() violation
    '''
    pass

def barrier():
    '''
    barrier()
    
    In a jug file, it assures that all tasks defined up to now have been
    completed. If not, parsing will (temporarily) stop at that point.

    This ensures that, after calling ``barrier()`` you are free to call
    ``value()`` to get any needed results.

    See Also
    --------
    bvalue : function
        Restricted version of this function. Often faster
    ''' 
    # The reason to import here instead of at module level is that if some
    # other code does
    # jug.task.alltasks = []
    # we would still be referring to the old version
    from .task import alltasks
    for t in reversed(alltasks):
        if not t.can_load():
            raise BarrierError


def bvalue(t):
    '''
    value = bvalue(t)

    Works similarly to::

        barrier()
        value = value(t)

    except that it only checks that `t` is complete.

    This can be much faster than a full ``barrier()`` call.
    See Also
    --------
    barrier : function
        Checks that **all** tasks have results available.
    '''
    from .task import value
    try:
        return value(t)
    except:
        raise BarrierError


########NEW FILE########
__FILENAME__ = compound
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2013, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.


from .task import Task

def compound_task_execute(x, h):
    '''
    compound_task_execute

    This is an internal function. Do **not** use directly.
    '''
    Task.store.dump(x, h)
    return x

def CompoundTask(f, *args, **kwargs):
    '''
    task = CompoundTask(f, *args, **kwargs)

    `f` should be such that it returns a `Task`, which can depend on other
    Tasks (even recursively).

    If `f` cannot been loaded, then this becomes equivalent to::

        f(*args, **kwargs)

    However, if it can, then we get a pseudo-task which returns the same value
    without `f` ever being executed.

    Example
    -------
    ::

        def complex_operation(input):
            intermediates = [Task(process, parameter=i) for i in xrange(1000)]
            mean = Task(compute_mean, intermediates)
            return mean

        mean_value = CompoundTask(complex_operation, input)


    Parameters
    ----------
    f : function returning a ``jug.Task``

    Returns
    -------
    task : jug.Task
    '''
    from .task import alltasks
    task = Task(f, *args, **kwargs)
    if task.can_load():
        return task
    del alltasks[alltasks.index(task)]
    h = task.hash()
    del task
    inner = f(*args, **kwargs)
    compound = Task(compound_task_execute, inner, h)
    compound.__jug_hash__ = lambda : h
    compound._check_hash = lambda : None
    return compound

def CompoundTaskGenerator(f):
    '''
    @CompoundTaskGenerator
    def f(arg0, arg1, ...)
        ...

    Turns f from a function into a compound task generator.

    This means that calling ``f(arg0, arg1)`` results in:
    ``CompoundTask(f, arg0, arg1)``

    See Also
    --------
    TaskGenerator
    '''
    from functools import wraps
    @wraps(f)
    def ctask_generator(*args, **kwargs):
        return CompoundTask(f, *args, **kwargs)
    ctask_generator.f = f
    return ctask_generator

########NEW FILE########
__FILENAME__ = hash
# -*- coding: utf-8 -*-
# Copyright (C) 2011-2013, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

def hash_update(M, elems):
    '''
    M = hash_update(M, elems)

    Update the hash object ``M`` with the sequence ``elems``.

    Parameters
    ----------
    M : hashlib object
        An object on which the update method will be called
    elems : sequence of 2-tuples

    Returns
    -------
    M : hashlib object
        This is the same object as the argument
    '''
    from six.moves import cPickle as pickle
    from six.moves import map
    import six

    try:
        import numpy as np
    except ImportError:
        np = None
    for n,e in elems:
        M.update(pickle.dumps(n))
        if hasattr(e, '__jug_hash__'):
            M.update(e.__jug_hash__())
        elif type(e) in (list, tuple):
            M.update(repr(type(e)).encode('utf-8'))
            hash_update(M, enumerate(e))
        elif type(e) == set:
            M.update('set')
            # With randomized hashing, different runs of Python might result in
            # different orders, so sort. We cannot trust that all the elements
            # in the set will be comparable, so we convert them to their hashes
            # beforehand.
            items = list(map(hash_one, e))
            items.sort()
            hash_update(M, enumerate(items))
        elif type(e) == dict:
            M.update(six.b('dict'))
            items = [(hash_one(k),v) for k,v in e.items()]
            items.sort(key=(lambda k_v:k_v[0]))

            hash_update(M, items)
        elif np is not None and type(e) == np.ndarray:
            M.update(six.b('np.ndarray'))
            M.update(pickle.dumps(e.dtype))
            M.update(pickle.dumps(e.shape))
            try:
                buffer = e.data
                M.update(buffer)
            except:
                M.update(e.copy().data)
        else:
            M.update(pickle.dumps(e))
    return M

def new_hash_object():
    '''
    M = new_hash_object()

    Returns a new hash object

    Returns
    -------
    M : hashlib object
    '''
    import hashlib
    return hashlib.sha1()

def hash_one(obj):
    '''
    hvalue = hash_one(obj)

    Compute a hash from a single object

    Parameters
    ----------
    obj : object
        Hashable object

    Returns
    -------
    hvalue : str
    '''
    h = new_hash_object()
    hash_update(h, [('hash1', obj)])
    return h.hexdigest().encode('utf-8')


########NEW FILE########
__FILENAME__ = exit_checks
from sys import exit
def exit_if_file_exists(fname):
    '''Before each task execute, check if file exists. If so, exit.

    Note that a check is only performed before a Task is execute. Thus, jug
    will not exit immediately if it is executing another long-running task.

    Parameters
    ----------
    fname : str
        path to check
    '''
    from jug import hooks
    def check_file(_t):
        from os import path
        if path.exists(fname):
            exit(0)
    hooks.register_hook('execute.task-pre-execute', check_file)

def exit_when_true(f, function_takes_Task=False):
    '''Generic exit check.
    
    After each task, call function ``f`` and exit if it return true.

    Parameters
    ----------
    f : function
        Function to call
    function_takes_Task : boolean, optional
        Whether to call the function with the task just executed (default: False)
    '''

    from jug import hooks
    if not function_takes_Task:
        f = lambda t : f()
    def exit_when(t):
        if f(t):
           exit(0)
    hooks.register_hook('execute.task-executed1', exit_when)

def exit_after_n_tasks(n):
    '''Exit after a specific number of tasks have been executed
    
    Parameters
    ----------
    n : int
        Number of tasks to execute
    '''
    from jug import hooks
    # In newer Python, we could use nonlocal, but this is a work around
    # (http://stackoverflow.com/questions/9603278/is-there-something-like-nonlocal-in-python-3/9603491#9603491)
    executed = [0]
    def exit_after(_t):
        executed[0] += 1
        if executed[0] > n:
           exit(0)
    hooks.register_hook('execute.task-executed1', exit_after)

def exit_after_time(hours=0, minutes=0, seconds=0):
    '''Exit after a specific number of tasks have been executed

    Note that this only checks the time **after each task has finished
    executing**. Thus if you are using this to limit the amount of time each
    process takes, make sure to specify a lower limit than what is needed.

    Parameters
    ----------
    hours : number, optional
    minutes : number, optional
    seconds : number, optional
    '''
    from jug import hooks
    from time import time
    deadline = time()
    deadline += seconds
    deadline += 60*minutes
    deadline += 60*60*hours

    def check_time(_t):
        if time() >= deadline:
            exit(0)
    hooks.register_hook('execute.task-executed1', check_time)


########NEW FILE########
__FILENAME__ = register
# Copyright (C) 2014, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
# License: MIT

_hooks = {}

_known_hooks = set([
        'execute.task-executed1',
        'execute.task-pre-execute',
        ])

def jug_hook(name, args=(), kwargs={}):
    '''Call hook

    Calls ``f(*args, **kwargs)`` for all functions registered with name ``name``.

    Parameters
    ----------
    name : str
        Name
    args, kwargs
        passed to functions

    Returns
    -------
    res : list
        A list with the result of all the functions
    '''
    return [f(*args, **kwargs) for f in _hooks.get(name, [])]

def register_hook(name, f=None):
    '''Register a hook

    Known hooks

    execute.task-executed1(Task)
        A single task has been executed. This hook can call ``sys.exit`` to
        exit the jug process (technically, it needs to raise SystemExit).
        Return values are ignored.

    Parameters
    ----------
    name : str
        Identify the hook name
    f : function
        Function to call
    '''
    if name not in _known_hooks:
        raise ValueError('jug.register_hook: {} is not a known hook name (Known are {}.)'.format(name, list(_known_hooks)))
    if f is None:
        from functools import partial
        return partial(register_hook, name)
    _hooks.setdefault(name, []).append(f)

########NEW FILE########
__FILENAME__ = io
# -*- coding: utf-8 -*-
# Copyright (C) 2013, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
# LICENSE: MIT
'''
Jug.IO module

- write_task_out: write out results, possibly with metadata.
'''

from .task import TaskGenerator, Task

class NoLoad(object):
    def __init__(self, t):
        self.t = t

    def __jug_hash__(self):
        from .hash import hash_one
        return hash_one(['NoLoad', self.t.hash()])

    def __jug_value__(self):
        return self

@TaskGenerator
def _do_write_task_out(result_value, result, oname, metadata_fname=None, metadata_format='yaml'):
    from .task import describe
    if metadata_fname is not None:
        description = describe(result.t)
        if metadata_format.lower() == 'yaml':
            import yaml
            yaml.dump(description, open(metadata_fname, 'w'))
        elif metadata_format.lower() == 'json':
            import json
            json.dump(description, open(metadata_fname, 'w'))
        else:
            raise ValueError('jug.io.write_task_out: Unknown metadata format "{}" [supported are "yaml" and "json"]'.format(metadata_format))
    try:
        import numpy as np
        if isinstance(result_value, np.ndarray):
            np.save(result, oname)
            return
    except:
        pass
    if oname is not None:
        import pickle
        pickle.dump(result_value, open(oname, 'wb'))

def write_task_out(result, oname, metadata_fname=None, metadata_format='yaml'):
    '''
    write_task_out(result, oname, metadata_fname=None, metadata_format='yaml')

    Write out the results of a Task to file, possibly including metadata.

    If ``metadata_fname`` is not None, it should be the name of a file to which
    to write metadata on the computation.

    Parameters
    ----------
    result: a Task object
    oname : str
        The target output filename
    metadata_fname : str, optional
        If not None, metadata will be written to this file.
    metadata_format : str, optional
        What format to write data in. Currently, 'yaml' & 'json' are supported.
    '''

    return _do_write_task_out(result, NoLoad(result), oname, metadata_fname, metadata_format)

def write_metadata(result, metadata_fname, metadata_format='yaml'):
    '''
    write_metadata(result, metadata_fname, metadata_format='yaml')

    Write out the metadata on a Task out.


    Parameters
    ----------
    result: a Task object
    metadata_fname : str
        metadata will be written to this file.
    metadata_format : str, optional
        What format to write data in. Currently, 'yaml' & 'json' are supported.
    '''

    return _do_write_task_out(result, NoLoad(result), None, metadata_fname, metadata_format)

# Console status table output

import textwrap

def print_task_summary_table(options, groups):
    """Print task summary table given tasks groups.

    groups - [(group_title, {(task_name, count)})] grouped summary of tasks.
    """
    num_groups = len(groups)

    names = list()
    for _, group_data in groups:
        names.extend(n for n in group_data.keys() if not n in names) 

    termsize, termheight = get_terminal_size()
    name_width = termsize - (num_groups * 12) - 2

    line_format = ("%12s" * num_groups) + '  ' + '%-' + str(name_width) + 's'
    format_size = (12 * num_groups) + 2 + name_width

    options.print_out(line_format % tuple([g for g, _ in groups] + ["Task name"]))
    options.print_out('-' * format_size)

    for n in names:
        name_lines = textwrap.wrap(n, width=name_width - 4)
        options.print_out(line_format % tuple([g[n] for _, g in groups] + name_lines[:1]))

        for name_extension in name_lines[1:]:
            options.print_out(line_format % tuple( ([""] * num_groups) + [(" " * 4) + name_extension]))

    options.print_out('.' * format_size)
    options.print_out(line_format % tuple([sum(g.values()) for _,g in groups] + ["Total"]))
    options.print_out()

# Terminal size calculation

import os
import shlex
import struct
import platform
import subprocess
 
 
def get_terminal_size():
    """ get_terminal_size()
     - get width and height of console
     - works on linux,os x,windows,cygwin(windows)
     originally retrieved from:
     http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
    """
    current_os = platform.system()
    tuple_xy = None
    if current_os == 'Windows':
        tuple_xy = _get_terminal_size_windows()
        if tuple_xy is None:
            tuple_xy = _get_terminal_size_tput()
            # needed for window's python in cygwin's xterm!
    if current_os in ['Linux', 'Darwin'] or current_os.startswith('CYGWIN'):
        tuple_xy = _get_terminal_size_linux()
    if tuple_xy is None:
        tuple_xy = (80, 25)      # default value
    return tuple_xy

def _get_terminal_size_windows():
    try:
        from ctypes import windll, create_string_buffer
        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12
        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            (bufx, bufy, curx, cury, wattr,
             left, top, right, bottom,
             maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            sizex = right - left + 1
            sizey = bottom - top + 1
            return sizex, sizey
    except:
        pass

def _get_terminal_size_tput():
    # get terminal width
    # src: http://stackoverflow.com/questions/263890/how-do-i-find-the-width-height-of-a-terminal-window
    try:
        cols = int(subprocess.check_call(shlex.split('tput cols')))
        rows = int(subprocess.check_call(shlex.split('tput lines')))
        return (cols, rows)
    except:
        pass

def _get_terminal_size_linux():
    def ioctl_GWINSZ(fd):
        try:
            import fcntl
            import termios
            cr = struct.unpack('hh',
                               fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
            return cr
        except:
            pass
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (os.environ['LINES'], os.environ['COLUMNS'])
        except:
            return None
    return int(cr[1]), int(cr[0])

########NEW FILE########
__FILENAME__ = jug
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2014, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.


from collections import defaultdict
import sys
import os
import os.path
import re
import logging

from . import task
from .task import Task
from .io import print_task_summary_table
from .subcommands.status import status
from .subcommands.webstatus import webstatus
from .subcommands.shell import shell
from .barrier import BarrierError

def do_print(store, options):
    '''
    do_print(store, options)

    Print a count of task names.

    Parameters
    ----------
    store : jug backend
    options : jug options
    '''
    task_counts = defaultdict(int)
    for t in task.alltasks:
        task_counts[t.name] += 1

    print_task_summary_table(options, [("Count", task_counts)])

def invalidate(store, options):
    '''
    invalidate(store, options)

    Implements 'invalidate' command

    Parameters
    ----------
    store : jug.backend
    options : options object
        Most relevant option is `invalid_name`, a string  with the exact (i.e.,
        module qualified) name of function to invalidate
    '''
    invalid_name = options.invalid_name
    tasks = task.alltasks
    cache = {}
    if re.match( r'/.*?/', invalid_name):
        # Looks like a regular expression
        invalidate_re = re.compile( invalid_name.strip('/') )
    elif '.' in invalid_name:
        # Looks like a full task name
        invalidate_re = invalid_name.replace('.','\\.' )
    else:
        # A bare function name perhaps?
        invalidate_re = re.compile(r'\.' + invalid_name )
    def isinvalid(t):
        if isinstance(t, task.Tasklet):
            return isinvalid(t.base)
        h = t.hash()
        if h in cache:
            return cache[h]
        if re.search( invalidate_re, t.name ):
            cache[h] = True
            return True
        for dep in t.dependencies():
            if isinvalid(dep):
                cache[h] = True
                return True
        cache[h] = False
        return False

    invalid = list(filter(isinvalid, tasks))
    if not invalid:
        options.print_out('No results invalidated.')
        return
    task_counts = defaultdict(int)
    for t in invalid:
        if store.remove(t.hash()):
            task_counts[t.name] += 1
    if sum(task_counts.values()) == 0:
        options.print_out('Tasks invalidated, but no results removed')
    else:
        print_task_summary_table(options, [("Invalidated", task_counts)])

def _sigterm(_,__):
    sys.exit(1)

def execution_loop(tasks, options, tasks_executed, tasks_loaded):
    from time import sleep
    from .hooks import jug_hook

    logging.info('Execute start (%s tasks)' % len(tasks))
    while tasks:
        upnext = [] # tasks that can be run
        for i in range(int(options.execute_nr_wait_cycles)):
            max_cannot_run = min(len(tasks), 128)
            for i in range(max_cannot_run):
                # The argument for this is the following:
                # if T' is dependent on the result of T, it is better if the
                # processor that ran T, also runs T'. By having everyone else
                # push T' to the end of tasks, this is more likely to happen.
                #
                # Furthermore, this avoids always querying the same tasks.
                if tasks[0].can_run():
                    break
                tasks.append(tasks.pop(0))
            while tasks and tasks[0].can_run():
                upnext.append(tasks.pop(0))
            if upnext:
                break
            for ti,t in enumerate(tasks):
                if t.can_run():
                    upnext.append(tasks.pop(ti))
                    break
            if upnext:
                break
            logging.info('waiting %s secs for an open task...' % options.execute_wait_cycle_time_secs)
            sleep(int(options.execute_wait_cycle_time_secs))
        if not upnext:
            logging.info('No tasks can be run!')
            break
        for t in upnext:
            if t.can_load():
                logging.info('Loadable %s...' % t.name)
                tasks_loaded[t.name] += 1
                continue
            locked = False
            try:
                locked = t.lock()
                if t.can_load(): # This can be true if the task ran between the check above and this one
                    logging.info('Loadable %s...' % t.name)
                    tasks_loaded[t.name] += 1
                elif locked:
                    logging.info('Executing %s...' % t.name)
                    jug_hook('execute.task-pre-execute', (t,))

                    t.run(debug_mode=options.debug)
                    tasks_executed[t.name] += 1
                    jug_hook('execute.task-executed1', (t,))
                    if options.aggressive_unload:
                        t.unload_recursive()
                else:
                    logging.info('Already in execution %s...' % t.name)
            except SystemExit:
                raise
            except Exception as e:
                if options.pdb:
                    import sys
                    _,_, tb = sys.exc_info()

                    # The code below is a complex attempt to load IPython
                    # debugger which works with multiple versions of IPython.
                    #
                    # Unfortunately, their API kept changing prior to the 1.0.
                    try:
                        import IPython
                        try:
                            import IPython.core.debugger
                            try:
                                from IPython.terminal.ipapp import load_default_config
                                config = load_default_config()
                                colors = config.TerminalInteractiveShell.colors
                            except:
                                import IPython.core.ipapi
                                ip = IPython.core.ipapi.get()
                                colors = ip.colors
                            debugger = IPython.core.debugger.Pdb(colors)
                        except ImportError:
                            #Fallback to older version of IPython API
                            import IPython.ipapi
                            import IPython.Debugger
                            shell = IPython.Shell.IPShell(argv=[''])
                            ip = IPython.ipapi.get()
                            debugger = IPython.Debugger.Pdb(ip.options.colors)
                    except ImportError:
                        #Fallback to standard debugger
                        import pdb
                        debugger = pdb.Pdb()

                    debugger.reset()
                    debugger.interaction(None, tb)
                else:
                    import itertools
                    logging.critical('Exception while running %s: %s' % (t.name,e))
                    for other in itertools.chain(upnext, tasks):
                        for dep in other.dependencies():
                            if dep is t:
                                logging.critical('Other tasks are dependent on this one! Parallel processors will be held waiting!')
                if not options.execute_keep_going:
                    raise
            finally:
                if locked: t.unlock()
def execute(options):
    '''
    execute(options)

    Implement 'execute' command
    '''
    from signal import signal, SIGTERM

    signal(SIGTERM,_sigterm)
    tasks = task.alltasks
    tasks_executed = defaultdict(int)
    tasks_loaded = defaultdict(int)
    store = None
    noprogress = 0
    while noprogress < 2:
        del tasks[:]
        store,jugspace = init(options.jugfile, options.jugdir, store=store)
        if options.debug:
            for t in tasks:
                # Trigger hash computation:
                t.hash()

        previous = sum(tasks_executed.values())
        execution_loop(tasks, options, tasks_executed, tasks_loaded)
        after = sum(tasks_executed.values())
        done = not jugspace.get('__jug__hasbarrier__', False)
        if done:
            break
        if after == previous:
            from time import sleep
            noprogress += 1
            sleep(int(options.execute_wait_cycle_time_secs))
    else:
        logging.info('No tasks can be run!')



    print_task_summary_table(options, [("Executed", tasks_executed), ("Loaded", tasks_loaded)])

def cleanup(store, options):
    '''
    cleanup(store, options)

    Implement 'cleanup' command
    '''
    if options.cleanup_locks_only:
        removed = store.remove_locks()
    else:
        tasks = task.alltasks
        removed = store.cleanup(tasks)
    options.print_out('Removed %s files' % removed)


def check(store, options):
    '''
    check(store, options)

    Executes check subcommand

    Parameters
    ----------
    store : jug.backend
            backend to use
    options : jug options
    '''
    sys.exit(_check_or_sleep_until(store, False))

def sleep_until(store, options):
    '''
    sleep_until(store, options)

    Execute sleep-until subcommand

    Parameters
    ----------
    store : jug.backend
            backend to use
    options : jug options
        ignored
    '''
    sys.exit(_check_or_sleep_until(store, True))

def _check_or_sleep_until(store, sleep_until):
    from .task import recursive_dependencies
    tasks = task.alltasks
    active = set(tasks)
    for t in reversed(tasks):
        if t not in active:
            continue
        while not t.can_load(store):
            if sleep_until:
                from time import sleep
                sleep(12)
            else:
                return 1
        else:
            for dep in recursive_dependencies(t):
                try:
                    active.remove(dep)
                except KeyError:
                    pass
    return 0


def init(jugfile=None, jugdir=None, on_error='exit', store=None):
    '''
    store,jugspace = init(jugfile={'jugfile'}, jugdir={'jugdata'}, on_error='exit', store=None)

    Initializes jug (create backend connection, ...).
    Imports jugfile

    Parameters
    ----------
    jugfile : str, optional
        jugfile to import (default: 'jugfile')
    jugdir : str, optional
        jugdir to use (could be a path)
    on_error : str, optional
        What to do if import fails (default: exit)
    store : storage object, optional
        If used, this is returned as ``store`` again.

    Returns
    -------
    store : storage object
    jugspace : dictionary
    '''
    import imp
    from .options import set_jugdir
    assert on_error in ('exit', 'propagate'), 'jug.init: on_error option is not valid.'

    if jugfile is None:
        jugfile = 'jugfile'
    if store is None:
        store = set_jugdir(jugdir)
    sys.path.insert(0, os.path.abspath('.'))

    # The reason for this implementation is that it is the only that seems to
    # work with both barrier and pickle()ing of functions inside the jugfile
    #
    # Just doing __import__() will not work because if there is a BarrierError
    # thrown, then functions defined inside the jugfile end up in a confusing
    # state.
    #
    # Alternatively, just execfile()ing will make any functions defined in the
    # jugfile unpickle()able which makes mapreduce not work
    #
    # Therefore, we simulate (partially) __import__ and set sys.modules *even*
    # if BarrierError is raised.
    #
    jugmodname = os.path.basename(jugfile[:-len('.py')])
    jugmodule = imp.new_module(jugmodname)
    jugmodule.__file__ = os.path.abspath(jugfile)
    jugspace = jugmodule.__dict__
    sys.modules[jugmodname] = jugmodule
    jugfile_contents = open(jugfile).read()
    try:
        exec(compile(jugfile_contents, jugfile, 'exec'), jugspace, jugspace)
    except BarrierError:
        jugspace['__jug__hasbarrier__'] = True
    except Exception as e:
        logging.critical("Could not import file '%s' (error: %s)", jugfile, e)
        if on_error == 'exit':
            import traceback
            print(traceback.format_exc())
            sys.exit(1)
        else:
            raise

    # The store may have been changed by the jugfile.
    store = Task.store
    return store, jugspace


def main(argv=None):
    from .options import parse
    if argv is None:
        from sys import argv
    options = parse(argv[1:])
    store = None
    if options.cmd not in ('status', 'execute', 'webstatus'):
        store,jugspace = init(options.jugfile, options.jugdir)

    if options.cmd == 'execute':
        execute(options)
    elif options.cmd == 'count':
        do_print(store, options)
    elif options.cmd == 'check':
        check(store, options)
    elif options.cmd == 'sleep-until':
        sleep_until(store, options)
    elif options.cmd == 'status':
        status(options)
    elif options.cmd == 'invalidate':
        invalidate(store, options)
    elif options.cmd == 'cleanup':
        cleanup(store, options)
    elif options.cmd == 'shell':
        shell(store, options, jugspace)
    elif options.cmd == 'webstatus':
        webstatus(options)
    else:
        logging.critical('Jug: unknown command: \'%s\'' % options.cmd)
    if store is not None:
        store.close()

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        logging.critical('Unhandled Jug Error!')
        raise

########NEW FILE########
__FILENAME__ = jug_version
__version__ = '1.0'

########NEW FILE########
__FILENAME__ = mapreduce
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2013, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
# License : MIT

'''
mapreduce: Build tasks that follow a map-reduce pattern.
'''


from .jug import Task
from .utils import identity
from .hash import hash_one

from itertools import chain

__all__ = [
    'mapreduce',
    'map',
    'reduce',
    ]

def _get_function(f):
    if getattr(f, '_jug_is_task_generator', False):
        hvalue = hash_one(f)
        f = f.f
        f.__jug_hash__ = lambda: hvalue
        return f
    return f

def _jug_map_reduce(reducer, mapper, inputs):
    from six.moves import reduce
    reducer = _get_function(reducer)
    mapper = _get_function(mapper)
    return reduce(reducer, _jug_map(mapper, inputs))

def _jug_reduce(reducer, inputs):
    from six.moves import reduce
    reducer = _get_function(reducer)
    return reduce(reducer, chain(inputs))

def _break_up(lst, step):
    start = 0
    next = step
    while start < len(lst):
        yield lst[start:next]
        start = next
        next += step


def _jug_map(mapper, es):
    if mapper is None:
        mapper = lambda x: x
    return [mapper(e) for e in es]

def _jug_map_curry(mapper, es):
    return [mapper(*e) for e in es]


def mapreduce(reducer, mapper, inputs, map_step=4, reduce_step=8):
    '''
    task = mapreduce(reducer, mapper, inputs, map_step=4, reduce_step=8)

    Create a task that does roughly the following::

        reduce(reducer, map(mapper, inputs))

    Roughly because the order of operations might be different. In particular,
    `reducer` should be a true `reducer` functions (i.e., commutative and
    associative).

    Parameters
    ----------
    reducer : associative, commutative function
            This should map
                  Y_0,Y_1 -> Y'
    mapper : function from X -> Y
    inputs : list of X

    map_step : integer, optional
            Number of mapping operations to do in one go.
            This is what defines an inner task. (default: 4)
    reduce_step : integer, optional
            Number of reduce operations to do in one go.
            (default: 8)

    Returns
    -------
    task : jug.Task object
    '''
    reducers = [Task(_jug_map_reduce, reducer, mapper, input_i) for input_i in _break_up(inputs, map_step)]
    while len(reducers) > 1:
        reducers = [Task(_jug_reduce, reducer, reduce_i) for reduce_i in _break_up(reducers, reduce_step)]
    if len(reducers) == 0:
        return identity([])
    elif len(reducers) == 1:
        return reducers[0]
    else:
        assert False, 'This is a bug'

class block_access_slice(object):
    __slots__ = ('base', 'start', 'stop', 'stride', '_hvalue')
    def __init__(self, access, orig):
        self.base = access
        self.start,self.stop,self.stride = orig
        self._hvalue = None

    def __getitem__(self, p):
        if isinstance(p, slice):
            start,stop,stride = p.indices(len(self))
            return block_access_slice(self.base, (self.start + start, self.stop - (len(self)-stop), self.stride * stride))
        elif isinstance(p, int):
            p *= self.stride
            p += self.start
            if p >= self.stop:
                raise IndexError
            return self.base[p]
        else:
            raise TypeError

    def __len__(self):
        return self.stop - self.start

    def __jug_hash__(self):
        if self._hvalue is not None:
            return self._hvalue
        self._hvalue = hash_one({
            'type': 'map-access-slice',
            'base': self.base,
            'start': self.start,
            'stop': self.stop,
            'stride': self.stride,
        })
        return self._hvalue

    def __jug_value__(self):
        from .task import value
        return [value(self[i]) for i in range(len(self))]

class block_access(object):
    __slots__ = ('blocks','block_size', 'len','_hvalue')
    def __init__(self, blocks, block_size, len):
        self.blocks = blocks
        self.block_size = block_size
        self.len = len
        self._hvalue = None

    def __getitem__(self, p):
        if isinstance(p, slice):
            return block_access_slice(self, p.indices(self.len))
        elif isinstance(p, int):
            if not (0 <= p < self.len):
                raise IndexError
            b = p//self.block_size
            bi = p % self.block_size
            return self.blocks[b][bi]
        else:
            raise TypeError

    def __len__(self):
        return self.len

    def __jug_hash__(self):
        if self._hvalue is not None:
            return self._hvalue
        value = hash_one({
            'type': 'map-access',
            'len': self.len,
            'blocks': self.blocks,
            'block_size': self.block_size,
        })
        self._hvalue = value
        return value

    def __jug_value__(self):
        from .task import value
        return [value(self[i]) for i in range(len(self))]

def map(mapper, sequence, map_step=4):
    '''
    sequence' = map(mapper, sequence, map_step=4)

    Roughly equivalent to::

        sequence' = [Task(mapper,s) for s in sequence]

    except that the tasks are grouped in groups of `map_step`

    Parameters
    ----------
    mapper : function
        function from A -> B
    sequence : list of A
    map_step : integer, optional
        nr of elements to process per task. This should be set so that each
        task takes the right amount of time.

    Returns
    -------
    sequence' : list of B
        sequence'[i] = mapper(sequence[i])

    See Also
    --------
    mapreduce
    currymap: function
        Curried version of this function
    '''
    if map_step == 1:
        return [Task(mapper, s) for s in sequence]
    blocks = []
    n = 0
    for ss in _break_up(sequence, map_step):
        blocks.append(
            Task(_jug_map, _get_function(mapper), ss)
            )
        n += len(ss)
    return block_access(blocks, map_step, n)

def currymap(mapper, sequence, map_step=4):
    '''
    sequence' = currymap(mapper, sequence, map_step=4)

    Roughly equivalent to::

        sequence' = [Task(mapper,*s) for s in sequence]

    except that the tasks are grouped in groups of `map_step`

    Parameters
    ----------
    mapper : function
        function from A1 -> A2 ... -> An -> B
    sequence : list of (A1,A2,...,An)
    map_step : integer, optional
        nr of elements to process per task. This should be set so that each
        task takes the right amount of time.

    Returns
    -------
    sequence' : list of B
        sequence'[i] = mapper(*sequence[i])

    See Also
    --------
    mapreduce: function
    map: function
        Uncurried version of this function
    '''
    if map_step == 1:
        return [Task(mapper, *s) for s in sequence]
    result = []
    for ss in _break_up(sequence, map_step):
        t = Task(_jug_map_curry, _get_function(mapper), ss)
        for i,_ in enumerate(ss):
            result.append(t[i])
    return result




def reduce(reducer, inputs, reduce_step=8):
    '''
    task = reduce(reducer, inputs, reduce_step=8)

    Parameters
    ----------
    reducer : associative, commutative function
            This should map
                  Y_0,Y_1 -> Y'
    inputs : list of X
    reduce_step : integer, optional
            Number of reduce operations to do in one go.
            (default: 8)

    Returns
    -------
    task : jug.Task object

    See Also
    --------
    mapreduce
    '''
    return mapreduce(reducer, None, inputs, reduce_step=reduce_step)


########NEW FILE########
__FILENAME__ = options
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2012, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.
'''
Options

Options
-------
- jugdir: main jug directory.
- jugfile: filesystem name for the Jugfile
- cmd: command to run.
- aggressive_unload: --aggressive-unload
- invalid_name: --invalid
- argv: Arguments not captured by jug (for script use)
- print_out: Print function to be used for output (behaves like Python3's print)
'''

import logging
from datetime import datetime
import six
import sys

class Options(object):
    def __init__(self, next):
        self.next = next

    def copy(self):
        from copy import deepcopy
        return deepcopy(self)

    def __getattr__(self, name):
        if name == '__deepcopy__':
            raise AttributeError
        if name in self.__dict__:
            return self.__dict__[name]
        if self.__dict__.get('next') is None:
            raise AttributeError
        return getattr(self.__dict__['next'], name)

default_options = Options(None)

default_options.jugdir = '%(jugfile)s.jugdata'
default_options.jugfile = 'jugfile.py'
default_options.cmd = None
default_options.aggressive_unload = False
default_options.invalid_name = None
default_options.argv = None
default_options.print_out = six.print_
default_options.status_mode = 'no-cached'
default_options.status_cache_clear = False
default_options.pdb = False
default_options.verbose = 'quiet'
default_options.debug = False

default_options.cleanup_locks_only = False

default_options.execute_wait_cycle_time_secs = 12
default_options.execute_nr_wait_cycles = (30*60) // default_options.execute_wait_cycle_time_secs
default_options.execute_keep_going = False

default_options.status_cache_file = '.jugstatus.sqlite3'

_Commands = (
    'check',
    'cleanup',
    'count',
    'execute',
    'invalidate',
    'shell',
    'sleep-until',
    'status',
    'stats',
    'webstatus',
    )
_usage_string = \
'''jug SUBCOMMAND JUGFILE OPTIONS...

Subcommands
-----------
   execute:      Execute tasks
   status:       Print status
   check:        Returns 0 if all tasks are finished. 1 otherwise.
   sleep-until:  Wait until all tasks are done, then exit.
   counts:       Simply count tasks
   cleanup:      Cleanup: remove result files that are not used.
   invalidate:   Invalidate the results of a task
   shell:        Run a shell after initialization

General Options
---------------
--jugdir=JUGDIR
    Directory in which to save intermediate files
    You can use Python format syntax, the following variables are available:
        - date
        - jugfile (without extension)
    By default, the value of `jugdir` is "%(jugfile)s.jugdata"
--verbose=LEVEL
    Verbosity level ('DEBUG', 'INFO', 'QUIET')

execute OPTIONS
---------------
--aggressive-unload
    Aggressively unload data from memory. This causes many more reloading of
    information, but is necessary if keeping too much in memory is leading to
    memory errors.
--pdb
    Call interactive debugger on errors. Preferentially uses IPython debugger.
--debug
    Debug mode. This adds a little more error checking, thus it can be slower.
    However, it detects certain types of errors and prints an error message. If
    --pdb is passed, --debug is automatically implied, but the opposite is not
    true: you can use --debug mode without --pdb.
--keep-going
    Keep going after errors

invalidate OPTIONS
------------------
--invalid=TASK-NAME
    Task name to invalidate


Examples
--------

  jug status script.py
  jug execute script.py &
  jug execute script.py &
  jug status script.py
'''

_usage_simple = 'jug SUBCOMMAND [JUGFILE] [OPTIONS...]'

def usage(error=None):
    '''
    usage(error=None)

    Print an usage string and exit.
    '''
    import sys
    if error is not None:
        error += '\n'
        sys.stderr.write(error)
    print(_usage_string)
    sys.exit(1)

def _str_to_bool(s):
    return s.lower() not in ('', '0', 'false', 'off')

def read_configuration_file(fp=None):
    '''
    options = read_configuration_file(fp='~/.jug/configrc')

    Parse configuration file.

    Parameters
    ----------
    fp : inputfile, optional
        File to read. If not given, use
    '''
    if fp is None:
        from os import path
        fp = path.expanduser('~/.jug/configrc')
        try:
            fp = open(fp)
        except IOError:
            return Options(None)
    from six.moves import configparser
    config = configparser.RawConfigParser()
    config.readfp(fp)
    infile = Options(None)

    def attempt(section, entry, new_name, conv=None):
        try:
            value = config.get(section, entry)
            if conv is not None:
                value = conv(value)
            setattr(infile, new_name, value)
        except configparser.NoOptionError:
            pass
        except configparser.NoSectionError:
            pass
    attempt('main', 'jugdir', 'jugdir')
    attempt('main', 'jugfile', 'jugfile')

    attempt('status', 'cache', 'status_mode')

    attempt('cleanup', 'locks-only', 'cleanup_locks_only', bool)

    attempt('execute', 'aggressive-unload', 'aggressive_unload', _str_to_bool)
    attempt('execute', 'pbd', 'pdb', bool)
    attempt('execute', 'debug', 'debug', bool)
    attempt('execute', 'nr-wait-cycles', 'execute_nr_wait_cycles', int)
    attempt('execute', 'wait-cycle-time', 'execute_wait_cycle_time_secs', int)
    attempt('execute', 'keep-going', 'execute_keep_going', _str_to_bool)
    return infile


def parse(cmdlist=None, optionsfile=None):
    '''
    options.parse(cmdlist={sys.argv[1:]}, optionsfile=None)

    Parse the command line options and set the option variables.
    '''
    import optparse
    from .jug_version import __version__

    if cmdlist is None:
        cmdlist = sys.argv[1:]
    infile = read_configuration_file(optionsfile)
    infile.next = default_options
    cmdline = Options(infile)

    parser = optparse.OptionParser(usage=_usage_simple, version=__version__)
    parser.add_option(
                    '--aggressive-unload',
                    action='store_true',
                    dest='aggressive_unload',
                    help='Do not keep intermediate results in memory (for jobs which require a lot of memory)')
    parser.add_option('--invalid',action='store',dest='invalid_name')
    parser.add_option('--jugdir',
                    action='store',
                    dest='jugdir',
                    help='Where to save intermediate results')
    parser.add_option('--verbose',
                    action='store',
                    dest='verbose',
                    help='Verbosity level [use "info" to see details of processing]')
    parser.add_option('--cache',
                    action='store_true',
                    dest='cache',
                    help='Use a cache for faster status [does not update after jugfile changes, though]')
    parser.add_option('--cache-file',
                    action='store',
                    dest='status_cache_file',
                    help='Name of file to use for status cache. Use with status --cache.')
    parser.add_option('--clear',
                    action='store_true',
                    dest='status_cache_clear',
                    help='Use with status --cache. Removes the cache file')
    parser.add_option('--locks-only', action='store_true', dest='cleanup_locks_only')
    parser.add_option('--pdb',
                    action='store_true',
                    dest='pdb',
                    help='Drop to a PDB (debug) console on error')
    parser.add_option('--debug',
                    action='store_true',
                    dest='debug',
                    help='Turn on debug mode')
    parser.add_option('--nr-wait-cycles', action='store', dest='execute_nr_wait_cycles')
    parser.add_option('--keep-going', action='store_true', dest='execute_keep_going', help='For execute: continue after errors')
    parser.add_option('--wait-cycle-time', action='store', dest='execute_wait_cycle_time_secs')
    options,args = parser.parse_args(cmdlist)
    if not args:
        usage()
        return

    cmdline.cmd = args.pop(0)
    if args:
        cmdline.jugfile = args.pop(0)

    if cmdline.cmd not in _Commands:
        usage(error='No sub-command given')
        return
    if options.invalid_name and cmdline.cmd != 'invalidate':
        usage(error='invalid-name is only useful for invalidate subcommand')
        return
    if cmdline.cmd == 'invalidate' and not options.invalid_name:
        usage(error='invalidate subcommand requires ``invalid-name`` option')
        return

    cmdline.argv = args
    sys.argv = [cmdline.jugfile] + args
    if options.cache is not None:
        cmdline.status_mode = ('cached' if options.cache else 'no-cached')
    def _maybe_set(name):
        if getattr(options, name) is not None:
            setattr(cmdline, name, getattr(options, name))

    _maybe_set('jugdir')

    _maybe_set('verbose')
    _maybe_set('aggressive_unload')
    _maybe_set('invalid_name')
    _maybe_set('pdb')
    _maybe_set('debug')
    _maybe_set('execute_nr_wait_cycles')
    _maybe_set('execute_wait_cycle_time_secs')
    _maybe_set('execute_keep_going')
    _maybe_set('status_cache_clear')
    _maybe_set('status_cache_file')

    cmdline.jugdir = cmdline.jugdir % {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'jugfile': cmdline.jugfile[:-3],
                }
    try:
        nlevel = {
            'DEBUG' : logging.DEBUG,
            'INFO' : logging.INFO,
        }[cmdline.verbose.upper()]
        root = logging.getLogger()
        root.level = nlevel
    except KeyError:
        pass
    return cmdline


def set_jugdir(jugdir):
    '''
    store = set_jugdir(jugdir)

    Sets the jugdir. This is the programmatic equivalent of passing
    ``--jugdir=...`` on the command line.

    Parameters
    ----------
    jugdir : str

    Returns
    -------
    store : a jug backend
    '''
    from .task import Task
    from . import backends
    if jugdir is None:
        jugdir = 'jugdata'
    store = backends.select(jugdir)
    Task.store = store
    return store


########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2013, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.


from ..task import value

def load_all(jugspace, local_ns):
    '''
    load_all(jugspace, local_ns)

    Loads the result of all tasks.
    '''
    for k,v in jugspace.items():
        # ignore objects name like __this__
        if k.startswith('__') and k.endswith('__'): continue
        try:
            local_ns[k] = value(v)
        except Exception as e:
            print('Error while loading %s: %s' % (k, e))

_ipython_not_found_msg = '''\
jug: Error: could not import IPython libraries

IPython is necessary for `shell` command.
'''
_ipython_banner = '''
=========
Jug Shell
=========


Available jug functions:
    - value() : loads a specific object
    - load_all() : loads all objects

Enjoy...
'''

def shell(store, options, jugspace):
    '''
    shell(store, options, jugspace)

    Implement 'shell' command.

    Currently depends on Ipython being installed.
    '''
    try:
        from IPython.frontend.terminal.embed import InteractiveShellEmbed
        from IPython.frontend.terminal.ipapp import load_default_config
        config = load_default_config()
        ipshell = InteractiveShellEmbed(config=config, display_banner=_ipython_banner)
    except ImportError:
        try:
            # Fallback for older Python:
            from IPython.Shell import IPShellEmbed
            ipshell = IPShellEmbed(banner=_ipython_banner)
        except ImportError:
            import sys
            sys.stderr.write(_ipython_not_found_msg)
            sys.exit(1)

    def _load_all():
        '''
        load_all()

        Loads all task results.
        '''
        load_all(jugspace, local_ns)

    local_ns = {
        'load_all' : _load_all,
        'value' : value,
    }
    # This is necessary for some versions of Ipython. See:
    # http://groups.google.com/group/pylons-discuss/browse_thread/thread/312e3ead5967468a
    try:
        del jugspace['__builtins__']
    except KeyError:
        pass

    jugspace.update(local_ns)
    local_ns['__name__'] = '__jugfile__'
    ipshell(global_ns=jugspace, local_ns=local_ns)


########NEW FILE########
__FILENAME__ = status
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2014, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

from collections import defaultdict
from contextlib import contextmanager

import jug
from .. import task
from .. import backends
from ..task import Task
from ..backends import memoize_store
from ..io import print_task_summary_table

__all__ = [
    'status'
    ]

unknown = 'unknown'
waiting = 'waiting'
ready = 'ready'
running = 'running'
finished = 'finished'

def create_sqlite3(connection, ht, deps, rdeps):
    connection.executescript('''
    CREATE TABLE ht (
            id INTEGER PRIMARY KEY,
            name CHAR(128),
            hash CHAR(128),
            status INT);
    CREATE TABLE dep (
        source INT,
        target INT);
    ''')

    connection.executemany('INSERT INTO ht VALUES(?,?,?,?)', ht)

    for i,cdeps in deps.items():
        if len(cdeps):
            connection.executemany('''
               INSERT INTO dep(source, target) VALUES(?,?)
                ''', [(i,cd) for cd in cdeps])

def retrieve_sqlite3(connection):
    ht = connection. \
            execute('SELECT * FROM ht ORDER BY id'). \
            fetchall()
    deps = defaultdict(list)
    rdeps = defaultdict(list)
    for d0,d1 in connection.execute('SELECT * FROM dep'):
        deps[d0].append(d1)
        rdeps[d1].append(d0)
    return ht, dict(deps), dict(rdeps)

def save_dirty3(connection, dirty):
    connection.executemany('UPDATE ht SET STATUS = ? WHERE id = ?', [(nstatus,id) for id,nstatus in dirty.items()])

@contextmanager
def _open_connection(options):
    import sqlite3
    connection = sqlite3.connect(options.status_cache_file)
    yield connection
    connection.commit()
    connection.close()


def load_jugfile(options):
    store,_ = jug.init(options.jugfile, options.jugdir)
    h2idx = {}
    ht = []
    deps = {}
    for i,t in enumerate(task.alltasks):
        deps[i] = [h2idx[d.hash() if isinstance(d,Task) else d._base_hash()]
                        for d in t.dependencies()]
        hash = t.hash()
        ht.append( (i, t.name, hash, unknown) )
        h2idx[hash] = i

    rdeps = defaultdict(list)
    for k,v in deps.items():
        for rv in v:
            rdeps[rv].append(k)
    return store, ht, deps, dict(rdeps)


def update_status(store, ht, deps, rdeps):
    tasks_waiting = defaultdict(int)
    tasks_ready = defaultdict(int)
    tasks_running = defaultdict(int)
    tasks_finished = defaultdict(int)

    store = memoize_store(store, list_base=True)
    dirty = {}
    for i,name,hash,status in ht:
        nstatus = None
        if status == finished or store.can_load(hash):
            tasks_finished[name] += 1
            nstatus = finished
        else:
            can_run = True
            if status != ready:
                for dep in deps.get(i, []):
                    _,_,dhash,dstatus = ht[dep]
                    if dstatus != finished and not store.can_load(dhash):
                        can_run = False
                        break
            if can_run:
                lock = store.getlock(hash)
                if lock.is_locked():
                    tasks_running[name] += 1
                    nstatus = running
                else:
                    tasks_ready[name] += 1
                    nstatus = ready
            else:
                tasks_waiting[name] += 1
                nstatus = waiting
        assert nstatus is not None, 'update_status: nstatus not assigned'
        if status != nstatus:
            dirty[i] = nstatus
    return tasks_waiting, tasks_ready, tasks_running, tasks_finished, dirty


def _print_status(options, waiting, ready, running, finished):
    print_task_summary_table(options, [
                                ("Waiting", waiting),
                                ("Ready", ready),
                                ("Finished", finished),
                                ("Running", running)])


def _clear_cache(options):
    from os import unlink
    try:
        unlink(options.status_cache_file)
    except:
        pass

def _status_cached(options):
    create, update = list(range(2))
    try:
        with _open_connection(options) as connection:
            ht, deps, rdeps = retrieve_sqlite3(connection)
        store = backends.select(options.jugdir)
        mode = update
    except:
        store, ht, deps, rdeps = load_jugfile(options)
        mode = create

    tw,tre,tru,tf,dirty = update_status(store, ht, deps, rdeps)
    _print_status(options, tw, tre, tru, tf)
    if mode == update:
        with _open_connection(options) as connection:
            save_dirty3(connection, dirty)
    else:
        for k in dirty:
            _,name,hash,_ = ht[k]
            ht[k] = (k, name, hash, dirty[k])
        with _open_connection(options) as connection:
            create_sqlite3(connection, ht, deps, rdeps)
    return sum(tf.values())


def _status_nocache(options):
    store,_ = jug.init(options.jugfile, options.jugdir)
    Task.store = memoize_store(store, list_base=True)

    tasks_waiting = defaultdict(int)
    tasks_ready = defaultdict(int)
    tasks_running = defaultdict(int)
    tasks_finished = defaultdict(int)
    for t in task.alltasks:
        if t.can_load():
            tasks_finished[t.name] += 1
        elif t.can_run():
            if t.is_locked():
                tasks_running[t.name] += 1
            else:
                tasks_ready[t.name] += 1
        else:
            tasks_waiting[t.name] += 1
    _print_status(options, tasks_waiting, tasks_ready, tasks_running, tasks_finished)
    return sum(tasks_finished.values())


def status(options):
    '''
    status(options)

    Implements the status command.

    Parameters
    ----------
    options : jug options
    '''
    if options.status_mode == 'cached':
        try:
            import sqlite3
        except ImportError:
            from sys import stderr
            stderr.write('Cached status relies on sqlite3. Falling back to non-cached version')
            options.status_mode = 'no-cache'
            return status(options)
        if options.status_cache_clear:
            return _clear_cache(options)
        return _status_cached(options)
    else:
        return _status_nocache(options)

########NEW FILE########
__FILENAME__ = webstatus
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2012, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

from . import status as st

template = '''
<html>
<head>

<title>Jug Status :: %(jugfile)s</title>
<style>
body {
    width: 80%%;
    margin: auto;
    margin-top: 2em;
    font-family: sans-serif;
}
H1 {
    color: #D95550;
}
H1 .jugfile {
    color: #647704;
}

TH {
    color: #6d2243;
}
</style>
</head>
<body>
<h1>Jug Status for <span class="jugfile">%(jugfile)s</span></h1>
<table>
<tr>
    <th>Task Name</th>
    <th>Waiting</th>
    <th>Ready</th>
    <th>Executing</th>
    <th>Completed</th>
</tr>
%(table)s
</table>
</body>
'''
_row_template = '''
<tr>
    <th>%s</th>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
</tr>'''


def _format_counts(tw, tre, tru, tf):
    r = ''
    names = set()
    for t in [tw,tre,tru,tf]:
        names.update(list(t.keys()))
    for n in names:
        r += _row_template % (n, tw[n], tre[n], tru[n], tf[n])
    r += _row_template % ('', '', '', '', '')
    r += _row_template % ('Total',
                                sum(tw.values()),
                                sum(tre.values()),
                                sum(tru.values()),
                                sum(tf.values()))
    return r


def webstatus(options):
    import sqlite3
    connection = sqlite3.connect(':memory:', check_same_thread=False)
    store, ht, deps, rdeps = st.load_jugfile(options)
    st.create_sqlite3(connection, ht, deps, rdeps)

    try:
        import web
    except ImportError:
        from sys import stderr
        stderr.write('''
webstatus subcommand requires that web.py be installed (it could not be found).
You can try one of the following commands to install it:

    pip install web.py

or

    easy_install web.py
''')
        return
    urls = (
        '/(.*)', 'status'
    )
    class Status(object):
        def GET(self, name):
            ht, deps, rdeps = st.retrieve_sqlite3(connection)
            tw,tre,tru,tf,dirty = st.update_status(store, ht, deps, rdeps)
            st.save_dirty3(connection, dirty)
            return template % {
                    'jugfile' : options.jugfile,
                    'table' : _format_counts(tw, tre, tru, tf),
            }
    app = web.application(urls, {'status': Status})
    app.run()

########NEW FILE########
__FILENAME__ = task
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2013, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
# LICENSE: MIT
'''
Task: contains the Task class.

This is the main class for using jug.

There are two main alternatives:

- Use the ``Task`` class directly to build up tasks, such as ``Task(function, arg0, ...)``.
- Rely on the ``TaskGenerator`` decorator as a shortcut for this.
'''


from .hash import new_hash_object, hash_update, hash_one

__all__ = [
    'Task',
    'Tasklet',
    'recursive_dependencies',
    'TaskGenerator',
    'iteratetask',
    'value',
    ]

alltasks = []

class _getitem(object):
    def __init__(self, slice):
        self.slice = slice

    def __call__(self, obj):
        obj = value(obj)
        slice = value(self.slice)
        return obj[slice]

    def __jug_hash__(self):
        return hash_one(('jug.task._getitem', self.slice))

    def __repr__(self):
        return 'jug.task._getitem(%s)' % self.slice
    def __str__(self):
        return 'jug.task._getitem(%s)' % self.slice

class TaskletMixin(object):
    def __getitem__(self, slice):
        return Tasklet(self, _getitem(slice))

class Task(TaskletMixin):
    '''
    T = Task(f, dep0, dep1,..., kw_arg0=kw_val0, kw_arg1=kw_val1, ...)

    Defines a task, which is roughly equivalent to::

        f(dep0, dep1,..., kw_arg0=kw_val0, kw_arg1=kw_val1, ...)

    '''
    store = None
    # __slots__ = ('name', 'f', 'args', 'kwargs', '_hash','_lock')
    def __init__(self, f, *args, **kwargs):
        if getattr(f, 'func_name', '') == '<lambda>':
            raise ValueError('''jug.Task does not work with lambda functions!

Write an email to the authors if you feel you have a strong reason to use them (they are a bit
tricky to support since the general code relies on the function name)''')

        self.name = '%s.%s' % (f.__module__, f.__name__)
        self.f = f
        self.args = args
        self.kwargs = kwargs
        alltasks.append(self)

    def run(self, force=False, save=True, debug_mode=False):
        '''
        task.run(force=False, save=True)

        Performs the task.

        Parameters
        ----------
        force : boolean, optional
            if true, always run the task (even if it ran before)
            (default: False)
        save : boolean, optional
            if true, save the result to the store
            (default: True)
        '''
        assert self.can_run()
        if debug_mode: self._check_hash()
        self._result = self._execute()
        if save:
            name = self.hash()
            self.store.dump(self._result, name)
        if debug_mode: self._check_hash()
        return self._result

    def _execute(self):
        args = [value(dep) for dep in self.args]
        kwargs = dict((key,value(dep)) for key,dep in self.kwargs.items())
        return self.f(*args,**kwargs)


    def _get_result(self):
        if not hasattr(self, '_result'): self.load()
        return self._result

    result = property(_get_result, doc='Result value')
    def value(self):
        return self.result


    def can_run(self):
        '''
        bool = task.can_run()

        Returns true if all the dependencies have their results available.
        '''
        for dep in self.dependencies():
            if not hasattr(dep, '_result') and not dep.can_load():
                return False
        return True

    def is_loaded(self):
        '''
        loaded = task.is_loaded()

        Returns True if the task is already loaded
        '''
        return hasattr(self, '_result')

    def load(self):
        '''
        t.load()

        Loads the results from the storage backend.

        This function *always* loads from the backend even if the task is
        already loaded. You can use `is_loaded` as a check if you want to avoid
        this behaviour.

        Returns
        -------
        Nothing
        '''
        assert self.can_load()
        self._result = self.store.load(self.hash())

    def invalidate(self):
        '''
        t.invalidate()

        Equivalent to ``t.store.remove(t.hash())``. Useful for interactive use
        (i.e., in ``jug shell`` mode).
        '''
        self.store.remove(self.hash())

    def unload(self):
        '''
        t.unload()

        Unload results (can be useful for saving memory).
        '''
        if hasattr(self, '_result'):
            del self._result

    def unload_recursive(self):
        '''
        t.unload_recursive()

        Equivalent to::

            for tt in recursive_dependencies(t): tt.unload()
        '''
        def checked_unload_recursive(t, visited):
            if id(t) not in visited:
                visited.add(id(t))
                t.unload()
                for dep in t.dependencies():
                    checked_unload_recursive(dep, visited)

        checked_unload_recursive(self, set())

    def dependencies(self):
        '''
        for dep in task.dependencies():
            ...

        Iterates over all the first-level dependencies of task `t`

        Parameters
        ----------
        self : Task

        Returns
        -------
        deps : generator
            A generator over all of `self`'s dependencies

        See Also
        --------
        recursive_dependencies : retrieve dependencies recursively
        '''
        queue = [self.args, self.kwargs.values()]
        while queue:
            deps = queue.pop()
            for dep in deps:
                if isinstance(dep, (Task, Tasklet)):
                    yield dep
                elif isinstance(dep, (list, tuple)):
                    queue.append(dep)
                elif isinstance(dep, dict):
                    queue.append(iter(dep.values()))


    def can_load(self, store=None):
        '''
        bool = task.can_load()

        Returns whether result is available.
        '''
        if store is None:
            store = self.store
        return store.can_load(self.hash())

    def hash(self):
        '''
        fname = t.hash()

        Returns the hash for this task.

        The results are cached, so the first call can be much slower than
        subsequent calls.
        '''
        return self.__jug_hash__()

    def _compute_set_hash(self):
        M = new_hash_object()
        M.update(self.name.encode('utf-8'))
        hash_update(M, enumerate(self.args))
        hash_update(M, iter(self.kwargs.items()))
        value = M.hexdigest().encode('utf-8')
        self.__jug_hash__ = lambda : value
        return value


    def _check_hash(self):
        if self.hash() != self._compute_set_hash():
            hash_error_msg = ('jug error: Hash value of task (name: %s) changed unexpectedly.\n' % self.name)
            hash_error_msg += 'Typical cause is that a Task function changed the value of an argument (which messes up downstream computations).'
            raise RuntimeError(hash_error_msg)
    def __jug_hash__(self):
        return self._compute_set_hash()


    def __str__(self):
        '''String representation'''
        return 'Task: %s()' % self.name

    def __repr__(self):
        '''Detailed representation'''
        return 'Task(%s, args=%s, kwargs=%s)' % (self.name, self.args, self.kwargs)

    def lock(self):
        '''
        locked = task.lock()

        Tries to lock the task for the current process.

        Returns True if the lock was acquired. The correct usage pattern is::

            locked = task.lock()
            if locked:
                task.run()
            else:
                # someone else is already running this task!

        Not that using can_lock() can lead to race conditions. The above
        is the only fully correct method.

        Returns
        -------
        locked : boolean
            Whether the lock was obtained.
        '''
        if not hasattr(self, '_lock'):
            self._lock = self.store.getlock(self.hash())
        return self._lock.get()

    def unlock(self):
        '''
        task.unlock()

        Releases the lock.

        If the lock was not held, this may remove another thread's lock!
        '''
        self._lock.release()

    def is_locked(self):
        '''
        is_locked = t.is_locked()

        Note that only calling lock() and checking the result atomically checks
        for the lock(). This function can be much faster, though, and, therefore
        is sometimes useful.

        Returns
        -------
        is_locked : boolean
            Whether the task **appears** to be locked.

        See Also
        --------
        lock : create lock
        unlock : destroy lock
        '''
        if not hasattr(self, '_lock'):
            self._lock = self.store.getlock(self.hash())
        return self._lock.is_locked()

class Tasklet(TaskletMixin):
    '''
    Tasklet

    A Tasklet is a light-weight Task.

    It looks like a Task, behaves like a Task, but its results are not saved in
    the backend.

    It is useful for very simple functions and is automatically generated on
    subscripting a Task object::

        t = Task(f, 1)
        tlet = t[0]

    ``tlet`` will be a ``Tasklet``

    See Also
    --------
    Task
    '''
    def __init__(self, base, f):
        '''
        Tasklet equivalent to::

            f(value(base))
        '''
        self.base = base
        self.f = f
        self.unload = self.base.unload
        self.unload_recursive = self.base.unload_recursive

    def dependencies(self):
        yield self.base

    def value(self):
        return self.f(value(self.base))

    def can_load(self):
        return self.base.can_load()

    def _base_hash(self):
        if isinstance(self.base, Tasklet):
            return self.base._base_hash()
        return self.base.hash()

    def __jug_hash__(self):
        import six
        M = new_hash_object()
        M.update(six.b('Tasklet'))
        hash_update(M, [
                ('base', self.base),
                ('f', self.f),
            ])
        return M.hexdigest().encode('utf-8')

def topological_sort(tasks):
    '''
    topological_sort(tasks)

    Sorts a list of tasks topologically in-place. The list is sorted when
    there is never a dependency between tasks[i] and tasks[j] if i < j.
    '''
    sorted = []
    whites = set(tasks)
    def dfs(t):
        for dep in t.dependencies():
            if dep in whites:
                whites.remove(dep)
                dfs(dep)
        sorted.append(t)
    while whites:
        next = whites.pop()
        dfs(next)
    tasks[:] = sorted

def recursive_dependencies(t, max_level=-1):
    '''
    for dep in recursive_dependencies(t, max_level=-1):
        ...

    Returns a generator that lists all recursive dependencies of task

    Parameters
    ----------
    t : Task
        input task
    max_level : integer, optional
      Maximum recursion depth. Set to -1 or None for no recursion limit.

    Returns
    -------
    deps : generator
        A generator over all dependencies
    '''
    if max_level is None:
        max_level = -1
    if max_level == 0:
        return

    for dep in t.dependencies():
        yield dep
        for d2 in recursive_dependencies(dep, max_level - 1):
            yield d2

def value(elem):
    '''
    value = value(obj)

    Loads a task object recursively. This correcly handles lists,
    dictonaries and eny other type handled by the tasks themselves.

    Parameters
    ----------
    obj : object
        Anything that can be pickled or a Task

    Returns
    -------
    value : object
        The result of the task ``obj``
    '''
    if isinstance(elem, (Task, Tasklet)):
        return elem.value()
    elif type(elem) == list:
        return [value(e) for e in elem]
    elif type(elem) == tuple:
        return tuple([value(e) for e in elem])
    elif type(elem) == dict:
        return dict((x,value(y)) for x,y in elem.items())
    elif hasattr(elem, '__jug_value__'):
        return elem.__jug_value__()
    else:
        return elem

def CachedFunction(f,*args,**kwargs):
    '''
    value = CachedFunction(f, *args, **kwargs)

    is equivalent to::

        task = Task(f, *args, **kwargs)
        if not task.can_load():
            task.run()
        value = task.value()

    That is, it calls the function if the value is available,
    but caches the result for the future.

    Parameters
    ----------
    f : function
        Any function except unnamed (lambda) functions

    Returns
    -------
    value : result
        Result of calling ``f(*args,**kwargs)``

    See Also
    --------
    bvalue : function
        An alternative way to achieve similar results to ``CachedFunction(f)``
        using ``bvalue`` is::

            ft = Task(f)
            fvalue = bvalue(ft)

        The alternative method is more flexible, but will only be execute
        lazily. In particular, a ``jug status`` will not see past the
        ``bvalue`` call until ``jug execute`` is called to execute ``f``, while
        a ``CachedFunction`` object will always execute.

    '''
    t = Task(f,*args, **kwargs)
    if not t.can_load():
        if not t.can_run():
            raise ValueError('jug.CachedFunction: unable to run task %s' % t)
        t.run()
    return value(t)

class TaskGenerator(object):
    '''
    @TaskGenerator
    def f(arg0, arg1, ...)
        ...

    Turns f from a function into a task generator.

    This means that calling ``f(arg0, arg1)`` results in:
    ``Task(f, arg0, arg1)``
    '''
    _jug_is_task_generator = True
    def __init__(self, f):
        self.f = f

    def __getstate__(self):
        from sys import modules
        modname = getattr(self.f, '__module__', None)
        fname = self.f.__name__
        obj = getattr(modules[modname], fname, None)
        if modname is None or (obj is not self and obj is not self.f):
            raise RuntimeError('jug.TaskGenerator could not pickle function.\nA function must be defined at the top-module level')
        return modname,fname

    def __setstate__(self, state):
        from sys import modules
        modname,fname = state
        self.f = getattr(modules[modname], fname)

    def __call__(self, *args, **kwargs):
        return Task(self.f, *args, **kwargs)


# This is lower case to be used like a function
class iteratetask(object):
    '''
    for a in iteratetask(task, n):
        ...

    This creates an iterator that over the sequence ``task[0], task[1], ...,
    task[n-1]``.

    Parameters
    ----------
    task : Task(let)
    n : integer

    Returns
    -------
    iterator

    Bugs
    ----
    There is no error checking that you have not missed elements at the end!
    '''
    def __init__(self, base, n):
        self.base = base
        self.n = n

    def __getitem__(self, i):
        if i >= self.n: raise IndexError
        return self.base[i]

    def __len__(self):
        return self.n


def describe(t):
    '''
    description = describe(t)

    Return a recursive description of the computation.

    Parameters
    ----------
    t : object

    Returns
    -------
    description : obj
    '''
    if isinstance(t, Task):
        description = { 'name': t.name, }
        if len(t.args):
            description['args'] = [describe(a) for a in t.args]
        if len(t.kwargs):
            description['kwargs'] = dict([(k,describe(v)) for k,v in t.kwargs.iteritems()])
        meta = t.store.metadata(t)
        if meta is not None:
            description['meta'] = meta
        return description
    elif isinstance(t, Tasklet):
        return {
                'name': 'tasklet',
                'operation': repr(t.f),
                'base': describe(t.base)
        }
    elif isinstance(t, list):
        return [describe(ti) for ti in t]
    elif isinstance(t, dict):
        return dict([(k,describe(v)) for k,v in t.items()])
    elif isinstance(t, tuple):
        return tuple(list(t))
    return t


########NEW FILE########
__FILENAME__ = barrier_mapreduce
# This tests an important regression:
# adding the module to the module map *before* execfile()ing the jugfile makes
# this not work.

from jug import barrier, Task, value
import jug.mapreduce
import math
from functools import reduce

def double(x):
    val = math.sqrt(2.)*math.sqrt(2.)
    return x*val

two = jug.mapreduce.map(double, list(range(20)))
barrier()
def product(vals):
    import operator
    return reduce(operator.mul, vals)
values = product(value(two))

########NEW FILE########
__FILENAME__ = builtin_function
from jug import TaskGenerator
import numpy as np
array = TaskGenerator(np.array)
a8 = array(list(range(8)))

########NEW FILE########
__FILENAME__ = bvalue
from jug import barrier, Task, bvalue
import math

def double(x):
    return 2*x

two = Task(double,1)
two = bvalue(two)
four = 2*two

########NEW FILE########
__FILENAME__ = compound
from jug import barrier, value, TaskGenerator
from jug.utils import identity
from jug.compound import CompoundTaskGenerator

@TaskGenerator
def double(x):
    return 2*x

@CompoundTaskGenerator
def twice(x):
    return (double(x), double(x))

@TaskGenerator
def tadd(y):
    return y[0] + y[1]

eight = twice(4)
sixteen = tadd(eight)




########NEW FILE########
__FILENAME__ = compound_nonsimple
from jug import barrier, value, TaskGenerator
from jug.utils import identity
from jug.compound import CompoundTaskGenerator

@TaskGenerator
def double(x):
    return 2*x

@CompoundTaskGenerator
def twice(x):
    return (double(x), double(x))

@TaskGenerator
def tadd(y):
    return y[0] + y[1]

eight = twice(4)
barrier()
eight = identity(eight)
barrier()
sixteen = tadd(eight)



########NEW FILE########
__FILENAME__ = compound_wbarrier
from jug import barrier, value, TaskGenerator
from jug.compound import CompoundTaskGenerator

@TaskGenerator
def double(x):
    return 2*x

@CompoundTaskGenerator
def twice(x):
    x2 = double(x)
    barrier()
    return double(value(x2))

four = double(2)
sixteen = twice(four)


########NEW FILE########
__FILENAME__ = custom_hash_function
from jug import TaskGenerator
from jug.utils import CustomHash

hash_called = 0

def bad_hash(x):
    global hash_called
    hash_called += 1
    return ('%s' % x).encode('utf-8')

@TaskGenerator
def double(x):
    return 2*x

one = CustomHash(1, bad_hash)

two = double(one)


########NEW FILE########
__FILENAME__ = empty_mapreduce
import jug.mapreduce
import math

def double(x):
    val = math.sqrt(2.)*math.sqrt(2.)
    return x*val

two = jug.mapreduce.map(double, [])

########NEW FILE########
__FILENAME__ = iteratetask
from jug import Task
from jug.task import iteratetask

def double(xs):
    return [x*2 for x in xs]

vals = [0,1,2]
t = Task(double, vals)
t0,t1,t2 = iteratetask(t, 3)


########NEW FILE########
__FILENAME__ = mapgenerator
from jug import mapreduce, TaskGenerator

@TaskGenerator
def double(x):
    return 2*x

vs = list(range(16))
v2s = mapreduce.map(double, vs)

########NEW FILE########
__FILENAME__ = mapreduce_generator
from jug import TaskGenerator
import jug.mapreduce
import math

@TaskGenerator
def double(x):
    return x*2

@TaskGenerator
def sum2(a,b):
    return (a+b)

sumtwo = jug.mapreduce.mapreduce(sum2, double, list(range(10)))

########NEW FILE########
__FILENAME__ = simple
from jug import TaskGenerator

@TaskGenerator
def double(x):
    return x*2

@TaskGenerator
def sum2(a, b):
    return a + b

@TaskGenerator
def plus1(x):
    return x + 1

vals = list(range(8))
vals = list(map(double, vals))
vals = list(map(plus1, vals))
vals = [sum2(v, 2) for v in vals]
vals = [sum2(v, v) for v in vals]

########NEW FILE########
__FILENAME__ = sleep_until_tasklet
from jug import TaskGenerator

@TaskGenerator
def double(xs):
    return [x*2 for x in xs]

vs = [2,4]
vs = double(vs)
v0 = vs[0]
v02 = double([v0])


########NEW FILE########
__FILENAME__ = slice_task
from jug import TaskGenerator

@TaskGenerator
def zero():
    return 0

@TaskGenerator
def range10():
    return list(range(10))

@TaskGenerator
def double(x):
    return 2*x

r = range10()
z = zero()
r0 = r[z]
z2  = double(r0)

########NEW FILE########
__FILENAME__ = tasklets
from jug import Task, Tasklet

def double(xs):
    return [x*2 for x in xs]

def sum2(a, b):
    return a + b

def plus1(x):
    return x + 1

vals = [0,1,2,3,4,5,6,7]
t = Task(double, vals)
t0 = t[0]
t2 = t[2]
t0_2 = Task(sum2, t0, t2)
t0_2_1 = Tasklet(t0_2, plus1)


########NEW FILE########
__FILENAME__ = tasklet_simple
from jug import TaskGenerator

@TaskGenerator
def double(x):
    return x,2*x

x = 2
y = double(x)
z = double(y[0])


########NEW FILE########
__FILENAME__ = wbarrier
from jug import barrier, Task
import math

def double(x):
# this tests an important regression:
# using __import__ for the jugfile with barrier() would make this code **not** work
    val = math.sqrt(2.)*math.sqrt(2.)
    return x*val

two = Task(double,1)
barrier()
four = Task(double, two)

def make_call(f, arg):
    return f(arg)
eight = Task(make_call, double, four)

########NEW FILE########
__FILENAME__ = write_with_meta
from jug import TaskGenerator
from jug.io import write_task_out

@TaskGenerator
def double(x):
    return x*2

@TaskGenerator
def plus1(x):
    return x + 1

x = double(4)
x = plus1(double(x))
write_task_out(x, 'x.pkl', metadata_fname='x.meta.json', metadata_format='json')
write_task_out(x, 'x.pkl', metadata_fname='x.meta.yaml')

########NEW FILE########
__FILENAME__ = task_reset
from nose.tools import with_setup
import jug.task
from jug.backends.dict_store import dict_store

def _setup():
    jug.task.Task.store = dict_store()
    while jug.task.alltasks:
        jug.task.alltasks.pop()

def _teardown():
    jug.task.Task.store = None
    while jug.task.alltasks:
        jug.task.alltasks.pop()

task_reset = with_setup(_setup, _teardown)

########NEW FILE########
__FILENAME__ = test_barrier
import jug.jug
from jug.tests.task_reset import task_reset
from jug.tests.utils import simple_execute
from jug.options import default_options
from functools import reduce

@task_reset
def test_barrier():
    store, space = jug.jug.init('jug/tests/jugfiles/wbarrier.py', 'dict_store')
    assert 'four' not in space
    simple_execute()
    store, space = jug.jug.init('jug/tests/jugfiles/wbarrier.py', store)
    assert 'four' in space

    # This is a regression test:
    # a test version of jug would fail here:
    simple_execute()

def product(vals):
    import operator
    return reduce(operator.mul, vals)

@task_reset
def test_mapreduce_barrier():
    store, space = jug.jug.init('jug/tests/jugfiles/barrier_mapreduce.py', 'dict_store')
    assert 'values' not in space
    simple_execute()
    store, space = jug.jug.init('jug/tests/jugfiles/barrier_mapreduce.py', store)
    assert 'values' in space
    assert space['values'] == product(list(range(20)))
    simple_execute()

@task_reset
def test_barrier_once():
    import sys
    options = default_options.copy()
    options.jugdir = 'dict_store'
    options.jugfile = 'jug/tests/jugfiles/wbarrier.py'
    jug.jug.execute(options)
    assert 'four' in dir(sys.modules['wbarrier'])

@task_reset
def test_bvalue():
    store, space = jug.jug.init('jug/tests/jugfiles/bvalue.py', 'dict_store')
    assert 'four' not in space
    simple_execute()
    store, space = jug.jug.init('jug/tests/jugfiles/bvalue.py', store)
    assert 'four' in space
    assert space['four'] == 4



########NEW FILE########
__FILENAME__ = test_compound
import jug.compound
import jug.mapreduce
import numpy as np
from jug.backends.dict_store import dict_store
from jug.tests.utils import simple_execute
from jug.compound import CompoundTask
from jug.tests.test_mapreduce import mapper, reducer, dfs_run
from jug.tests.task_reset import task_reset

@task_reset
def test_compound():
    jug.task.Task.store = dict_store()
    A = np.random.rand(10000)
    x = CompoundTask(jug.mapreduce.mapreduce,reducer, mapper, A)
    dfs_run(x)
    y = CompoundTask(jug.mapreduce.mapreduce,reducer, mapper, A)

    assert y.can_load()
    assert y.result == x.result


@task_reset
def test_w_barrier():
    store, space = jug.jug.init('jug/tests/jugfiles/compound_wbarrier.py', 'dict_store')
    simple_execute()
    store, space = jug.jug.init('jug/tests/jugfiles/compound_wbarrier.py', store)
    simple_execute()
    assert 'sixteen' in space
    assert space['sixteen'].result == 16


@task_reset
def test_non_simple():
    store, space = jug.jug.init('jug/tests/jugfiles/compound_nonsimple.py', 'dict_store')
    simple_execute()
    store, space = jug.jug.init('jug/tests/jugfiles/compound_nonsimple.py', store)
    simple_execute()
    store, space = jug.jug.init('jug/tests/jugfiles/compound_nonsimple.py', store)
    simple_execute()
    assert 'sixteen' in space
    assert space['sixteen'].result == 16

@task_reset
def test_non_simple():
    store, space = jug.jug.init('jug/tests/jugfiles/compound.py', 'dict_store')
    simple_execute()
    assert 'sixteen' in space
    assert space['sixteen'].result == 16
    store, space = jug.jug.init('jug/tests/jugfiles/compound.py', store)
    assert 'sixteen' in space
    assert space['sixteen'].result == 16

@task_reset
def test_debug():
    from jug.jug import execution_loop
    from jug.task import alltasks
    from jug.options import default_options
    from collections import defaultdict
    options = default_options.copy()
    options.debug = True

    store, space = jug.jug.init('jug/tests/jugfiles/compound.py', 'dict_store')
    execution_loop(alltasks, options, defaultdict(int), defaultdict(int))
    assert 'sixteen' in space
    assert space['sixteen'].result == 16
    store, space = jug.jug.init('jug/tests/jugfiles/compound.py', store)
    assert 'sixteen' in space
    assert space['sixteen'].result == 16


########NEW FILE########
__FILENAME__ = test_encode
from six import BytesIO
import six
from jug.backends.encode import compress_stream, decompress_stream, encode, decode
import numpy as np
def test_encode():
    assert decode(encode(None)) is None
    assert decode(encode([])) == []
    assert decode(encode(list(range(33)))) == list(range(33))

def test_numpy():
    assert np.all(decode(encode(np.arange(33))) == np.arange(33))


def test_decompress_stream_seek():
    s = encode(list(range(33)))
    st = decompress_stream(BytesIO(s))
    first = st.read(6)
    st.seek(-6, 1)
    second = st.read(6)
    assert first == second

    st = decompress_stream(BytesIO(s))
    first = st.read(6)
    st.seek(-6, 1)
    second = st.read(8)
    assert first == second[:6]

    st = decompress_stream(BytesIO(s))
    st.seek( 6, 1)
    st.seek(-6, 1)
    second = st.read(8)
    assert first == second[:6]

def test_decompress_stream_readline():
    text = six.b("1\n2\n3\n4")
    s = BytesIO()
    cstream = compress_stream(s)
    cstream.write(text)
    cstream.flush()
    dstream = decompress_stream(BytesIO(s.getvalue()))
    assert dstream.readline() == six.b("1\n")
    assert dstream.readline() == six.b("2\n")
    assert dstream.readline() == six.b("3\n")
    assert dstream.readline() == six.b("4")
    assert dstream.readline() == six.b("")


class Derived(np.ndarray):
    def __new__(cls, value):
        return np.ndarray.__new__(cls, value)

def test_numpy_derived():
    a = Derived([1,2,3])
    assert type(decode(encode(a))) == type(a)

########NEW FILE########
__FILENAME__ = test_hash
from jug.hash import new_hash_object, hash_update, hash_one
import numpy as np


def test_hash_numpy():
    A = np.arange(10, dtype=np.float32)
    dig0 = hash_one(A)
    A += 1
    dig1 = hash_one(A)
    assert dig0 != dig1
    A = np.zeros((20,20), np.float32)
    A[2,::2] = np.arange(10)
    dig2 = hash_one(A[2,::2])
    assert dig0 == dig2
    dig3 = hash_one(A[2,::2].astype(np.float64))
    assert dig3 != dig0

def test_dict_mixed():
    value = {
            frozenset([1,2,3]) : 4,
            'hello': 2
    }
    v = hash_one(value)
    assert len(v)

def test_hash_numpy_copy():
    X = np.arange(10)
    assert hash_one(X[::-1]) != hash_one(X)
    assert hash_one(X.copy()) == hash_one(X)

########NEW FILE########
__FILENAME__ = test_io
import jug.jug
from jug.tests.utils import simple_execute
from jug.backends.dict_store import dict_store
from .task_reset import task_reset
from jug.task import describe
from nose.tools import with_setup

def remove_files(flist, dlist):
    def teardown():
        from os import unlink
        for f in flist:
            try:
                unlink(f)
            except:
                pass
        from shutil import rmtree
        for dir in dlist:
            try:
                rmtree(dir)
            except:
                pass
    return with_setup(None, teardown)

@task_reset
def test_describe():
    jugfile = 'jug/tests/jugfiles/simple.py'
    store, space = jug.jug.init(jugfile, 'dict_store')
    simple_execute()
    t = space['vals'][0]
    desc = describe(t)
    assert len(desc['args']) == len(t.args)

@remove_files(['x.pkl', 'x.meta.yaml', 'x.meta.json'], ['testing_TO_DELETE.jugdata'])
@task_reset
def test_describe():
    jugfile = 'jug/tests/jugfiles/write_with_meta.py'
    store, space = jug.jug.init(jugfile, 'testing_TO_DELETE.jugdata')
    simple_execute()
    x = space['x']
    desc = describe(x)
    import json
    assert desc == json.load(open('x.meta.json'))
    import yaml
    assert desc == yaml.load(open('x.meta.yaml'))

########NEW FILE########
__FILENAME__ = test_jug_check
import jug.jug
import jug.task
from jug.task import Task
from jug.backends.dict_store import dict_store
from jug.tests.task_reset import task_reset
from jug.tests.utils import simple_execute
from jug.options import Options, default_options

import random
jug.jug.silent = True

def test_jug_check():
    N = 16
    A = [False for i in range(N)]
    def setAi(i):
        A[i] = True
        return i
    def first_two(one, two):
        return one+two

    setall = [Task(setAi, i) for i in range(N)]
    check = Task(first_two, setall[0], setall[1])
    check2 = Task(first_two, setall[1], setall[2])
    store = dict_store()
    jug.task.Task.store = store
    try:
        jug.jug.check(store, default_options)
    except SystemExit as e:
        assert e.code == 1
    else:
        assert False
    savedtasks = jug.task.alltasks[:]
    simple_execute()
    jug.task.alltasks = savedtasks

    try:
        jug.jug.check(store, default_options)
        assert False
    except SystemExit as e:
        assert e.code == 0
    else:
        assert False


@task_reset
def test_tasklet():
    jugfile = 'jug/tests/jugfiles/sleep_until_tasklet.py'
    store, space = jug.jug.init(jugfile, 'dict_store')
    assert 'four' not in space
    simple_execute()
    store, space = jug.jug.init(jugfile, store)
    assert jug.jug._check_or_sleep_until(store, False) == 0
    assert jug.jug._check_or_sleep_until(store, True) == 0
    
    

########NEW FILE########
__FILENAME__ = test_jug_execute
import jug.jug
import jug.task
from jug.task import Task
from jug.tests.utils import simple_execute
from jug.backends.dict_store import dict_store
import random
jug.jug.silent = True

def test_jug_execute_simple():
    N = 1024
    random.seed(232)
    A = [False for i in range(N)]
    def setAi(i):
        A[i] = True
    setall = [Task(setAi, i) for i in range(N)]
    store = dict_store()
    jug.task.Task.store = store
    simple_execute()
    assert False not in A
    assert max(store.counts.values()) < 4

def test_jug_execute_deps():
    N = 256
    random.seed(234)
    A = [False for i in range(N)]
    def setAi(i, other):
        A[i] = True
    idxs = list(range(N))
    random.shuffle(idxs)
    prev = None
    for idx in idxs:
        prev = Task(setAi, idx, prev)
    store = dict_store()
    jug.task.Task.store = store
    simple_execute()
    assert False not in A
    assert max(store.counts.values()) < 4

from .task_reset import task_reset
def test_aggressive_unload():
    from jug.jug import execution_loop
    from jug.task import alltasks
    from jug.options import default_options
    from collections import defaultdict
    options = default_options.copy()
    options.aggressive_unload = True
    @task_reset
    def run_jugfile(jugfile):
        store, space = jug.jug.init(jugfile, 'dict_store')
        execution_loop(alltasks, options, defaultdict(int), defaultdict(int))
    yield run_jugfile, 'jug/tests/jugfiles/tasklet_simple.py'
    yield run_jugfile, 'jug/tests/jugfiles/tasklets.py'
    yield run_jugfile, 'jug/tests/jugfiles/barrier_mapreduce.py'
    yield run_jugfile, 'jug/tests/jugfiles/compound_nonsimple.py'
    yield run_jugfile, 'jug/tests/jugfiles/slice_task.py'


########NEW FILE########
__FILENAME__ = test_jug_invalidate
from nose.tools import with_setup
import jug.jug
import jug.task
from jug.task import Task
from jug.backends.dict_store import dict_store
from jug.options import Options, default_options
from jug.tests.utils import simple_execute
from jug.tests.task_reset import task_reset
import random
jug.jug.silent = True


@task_reset
def test_jug_invalidate():
    def setAi(i):
        A[i] = True
    N = 1024
    A = [False for i in range(N)]
    setall = [Task(setAi, i) for i in range(N)]
    store = dict_store()
    jug.task.Task.store = store
    for t in setall: t.run()

    opts = Options(default_options)
    opts.invalid_name = setall[0].name
    jug.jug.invalidate(store, opts)
    assert not list(store.store.keys()), list(store.store.keys())
    jug.task.Task.store = dict_store()

@task_reset
def test_complex():
    store, space = jug.jug.init('jug/tests/jugfiles/tasklets.py', 'dict_store')
    simple_execute()

    store, space = jug.jug.init('jug/tests/jugfiles/tasklets.py', store)
    opts = Options(default_options)
    opts.invalid_name = space['t'].name
    h = space['t'].hash()
    assert store.can_load(h)
    jug.jug.invalidate(store, opts)
    assert not store.can_load(h)

@task_reset
def test_cleanup():
    store, space = jug.jug.init('jug/tests/jugfiles/tasklets.py', 'dict_store')
    h = space['t'].hash()
    simple_execute()

    opts = Options(default_options)
    opts.cleanup_locks_only = True
    assert store.can_load(h)
    jug.jug.cleanup(store, opts)
    assert store.can_load(h)
    opts.cleanup_locks_only = False
    jug.jug.cleanup(store, opts)
    assert not store.can_load(h)


########NEW FILE########
__FILENAME__ = test_lock
from jug.backends.file_store import file_store, file_based_lock
from nose.tools import with_setup

_storedir = 'jugtests'
def _remove_file_store():
    file_store.remove_store(_storedir)

@with_setup(teardown=_remove_file_store)
def test_twice():
    lock = file_based_lock(_storedir, 'foo')
    assert lock.get()
    assert not lock.get()
    lock.release()

    assert lock.get()
    assert not lock.get()
    lock.release()

@with_setup(teardown=_remove_file_store)
def test_twolocks():
    foo = file_based_lock(_storedir, 'foo')
    bar = file_based_lock(_storedir, 'bar')
    assert foo.get()
    assert bar.get()
    assert not foo.get()
    assert not bar.get()
    foo.release()
    bar.release()


########NEW FILE########
__FILENAME__ = test_mapreduce
import numpy as np

import jug.mapreduce
from jug.backends.dict_store import dict_store
from jug.tests.utils import simple_execute
from jug.mapreduce import _break_up, _get_function
from jug import value, TaskGenerator
from jug.tests.task_reset import task_reset
import jug.utils
from functools import reduce

def mapper(x):
    return x**2
def reducer(x, y):
    return x + y
def dfs_run(t):
    for dep in t.dependencies():
        dfs_run(dep)
    t.run()

def mapper2(x,y):
    return x+y

def test_get_function():
    oid = id(reducer)
    assert oid == id(_get_function(reducer))
    task_reducer = TaskGenerator(reducer)
    assert oid == id(_get_function(task_reducer))


@task_reset
def test_mapreduce():
    np.random.seed(33)
    jug.task.Task.store = dict_store()
    A = np.random.rand(10000)
    t = jug.mapreduce.mapreduce(reducer, mapper, A)
    dfs_run(t)
    assert np.abs(t.result - (A**2).sum()) < 1.

@task_reset
def test_map():
    np.random.seed(33)
    jug.task.Task.store = dict_store()
    A = np.random.rand(10000)
    ts = jug.mapreduce.map(mapper, A)
    simple_execute()
    ts = value(ts)
    assert np.all(ts == np.array(list(map(mapper,A))))

@task_reset
def test_reduce():
    np.random.seed(33)
    jug.task.Task.store = dict_store()
    A = np.random.rand(128)
    A = (A*32).astype(int) # This makes the reduction exactly cummutative (instead of approximately so as with floating point)
    t = jug.mapreduce.reduce(reducer, A)
    dfs_run(t)
    assert t.value() == reduce(reducer,A)

def test_break_up():
    for i in range(2,105):
        assert reduce(lambda a,b: a+b, _break_up(list(range(100)), i), []) == list(range(100))

@task_reset
def test_empty_mapreduce():
    store, space = jug.jug.init('jug/tests/jugfiles/empty_mapreduce.py', 'dict_store')
    simple_execute()
    assert value(space['two']) == []

@task_reset
def test_taskgenerator_mapreduce():
    store, space = jug.jug.init('jug/tests/jugfiles/mapreduce_generator.py', 'dict_store')
    simple_execute()
    assert space['sumtwo'].result == 2*sum(range(10))

@task_reset
def test_taskgenerator_map():
    store, space = jug.jug.init('jug/tests/jugfiles/mapgenerator.py', 'dict_store')
    simple_execute()
    assert len(value(space['v2s'])) == 16

@task_reset
def test_currymap():
    np.random.seed(33)
    jug.task.Task.store = dict_store()
    A = np.random.rand(100)
    ts = jug.mapreduce.currymap(mapper2, list(zip(A,A)))
    simple_execute()
    assert np.allclose(np.array(value(ts)) , A*2)


########NEW FILE########
__FILENAME__ = test_options
import jug.options

from six import StringIO
from nose.tools import raises

def test_chaining():
    first = jug.options.Options(None)
    second = jug.options.Options(first)
    third = jug.options.Options(second)

    first.one = 'one'
    second.two = 'two'
    third.three = 'three'

    assert third.one == 'one'
    first.one = 1
    assert third.one == 1
    assert second.one == 1
    assert second.two == 'two'
    assert third.three == 'three'
    @raises(AttributeError)
    def not_present_key(obj, key):
        return obj.key

    yield not_present_key, first, 'two'
    yield not_present_key, second, 'three'

_options_file = '''
[main]
jugfile=myjugfile.py

[execute]
wait-cycle-time=23
'''

def test_parse():
    parsed = jug.options.parse(
        ["execute", "--pdb"],
        StringIO(_options_file))

    assert parsed.jugfile == 'myjugfile.py'
    assert parsed.pdb
    assert parsed.execute_wait_cycle_time_secs == 23
    assert not parsed.aggressive_unload

def test_copy():
    parsed = jug.options.parse(
        ["execute", "--pdb"],
        StringIO(_options_file))
    copy = parsed.copy()
    assert parsed.pdb
    assert not parsed.aggressive_unload

def test_bool():
    from jug.options import _str_to_bool
    assert not _str_to_bool("")
    assert not _str_to_bool("0")
    assert not _str_to_bool("false")
    assert not _str_to_bool("FALSE")
    assert not _str_to_bool("off")
    assert _str_to_bool("on")
    assert _str_to_bool("true")
    assert _str_to_bool("1")

########NEW FILE########
__FILENAME__ = test_status
from jug.subcommands import status
from jug.tests.task_reset import task_reset
from jug.tests.utils import simple_execute
from jug.options import default_options
import jug

@task_reset
def test_nocache():
    store, space = jug.jug.init('jug/tests/jugfiles/simple.py', 'dict_store')
    simple_execute()

    options = default_options.copy()
    options.jugdir = store
    options.jugfile = 'jug/tests/jugfiles/simple.py'
    options.verbose = 'quiet'
    assert status.status(options) == 8 * 4

@task_reset
def test_cache():
    store, space = jug.jug.init('jug/tests/jugfiles/simple.py', 'dict_store')

    options = default_options.copy()
    options.jugdir = store
    options.jugfile = 'jug/tests/jugfiles/simple.py'
    options.verbose = 'quiet'
    options.status_mode = 'cached'
    options.status_cache_file = ':memory:'

    assert status.status(options) == 0
    simple_execute()
    assert status.status(options) == 8 * 4

@task_reset
def test_cache_bvalue():
    store, space = jug.jug.init('jug/tests/jugfiles/bvalue.py', 'dict_store')

    options = default_options.copy()
    options.jugdir = store
    options.jugfile = 'jug/tests/jugfiles/bvalue.py'
    options.verbose = 'quiet'
    options.status_mode = 'cached'
    options.status_cache_file = ':memory:'

    assert status.status(options) == 0
    simple_execute()
    assert status.status(options) == 1


########NEW FILE########
__FILENAME__ = test_store
import jug.backends.redis_store
import jug.backends.file_store
import jug.backends.dict_store
from jug.backends.redis_store import redis
from nose.tools import with_setup
from nose import SkipTest
import six

_storedir = 'jugtests'
def _remove_file_store():
    jug.backends.file_store.file_store.remove_store(_storedir)


def test_stores():
    def load_get(store):
        try:
            assert len(list(store.list())) == 0
            key = six.b('jugisbestthingever')
            assert not store.can_load(key)
            object = list(range(232))
            store.dump(object, key)
            assert store.can_load(key)
            assert store.load(key) == object
            assert len(list(store.list())) == 1
            store.remove(key)
            assert not store.can_load(key)
            store.close()
        except redis.ConnectionError:
            raise SkipTest()


    def lock(store):
        try:
            assert len(list(store.listlocks())) == 0
            key = six.b('jugisbestthingever')
            lock = store.getlock(key)
            assert not lock.is_locked()
            assert lock.get()
            assert not lock.get()
            lock2 = store.getlock(key)
            assert not lock2.get()
            assert len(list(store.listlocks())) == 1
            lock.release()
            assert lock2.get()
            lock2.release()
            store.close()
        except redis.ConnectionError:
            raise SkipTest()
    def lock_remove(store):
        try:
            assert len(list(store.listlocks())) == 0
            key = six.b('jugisbestthingever')
            lock = store.getlock(key)
            assert not lock.is_locked()
            assert lock.get()
            assert not lock.get()
            assert len(list(store.listlocks())) == 1
            store.remove_locks()
            assert len(list(store.listlocks())) == 0
            store.close()
        except redis.ConnectionError:
            raise SkipTest()
    functions = (load_get, lock, lock_remove)
    stores = [
            lambda: jug.backends.file_store.file_store('jugtests'),
            jug.backends.dict_store.dict_store,
            ]
    if redis is not None:
        stores.append(
            lambda: jug.redis_store.redis_store('redis:')
            )
    teardowns = (None, _remove_file_store, None)
    for f in functions:
        for s,tear in zip(stores,teardowns):
            f.teardown = tear
            yield f, s()

@with_setup(teardown=_remove_file_store)
def test_numpy_array():
    try:
        import numpy as np
    except ImportError:
        raise SkipTest()
    store = jug.backends.file_store.file_store(_storedir)
    arr = np.arange(100) % 17
    arr = arr.reshape((10,10))
    key = 'mykey'
    store.dump(arr, key)
    arr2 = store.load(key)
    assert np.all(arr2 == arr)
    store.remove(key)
    store.close()

########NEW FILE########
__FILENAME__ = test_tasklet
from jug.tests.task_reset import task_reset
from jug.tests.utils import simple_execute
from jug import task
import jug.jug

@task_reset
def test_tasklets():
    store, space = jug.jug.init('jug/tests/jugfiles/tasklets.py', 'dict_store')
    simple_execute()
    assert space['t0'].value() == 0
    assert space['t2'].value() == 4
    assert space['t0_2'].value() == 4
    assert space['t0_2_1'].value() == 5

@task_reset
def test_iteratetask():
    store, space = jug.jug.init('jug/tests/jugfiles/iteratetask.py', 'dict_store')
    simple_execute()
    assert space['t0'].value() == 0
    assert space['t1'].value() == 2
    assert space['t2'].value() == 4

@task_reset
def test_tasklet_dependencies():
    store, space = jug.jug.init('jug/tests/jugfiles/tasklets.py', 'dict_store')
    assert not space['t0_2'].can_run()


@task_reset
def test_tasklet_dependencies():
    store, space = jug.jug.init('jug/tests/jugfiles/slice_task.py', 'dict_store')
    simple_execute()
    assert space['z2'].value() == 0



########NEW FILE########
__FILENAME__ = test_tasks
from nose.tools import with_setup
import jug.task
from jug.backends.dict_store import dict_store
from jug.tests.task_reset import task_reset
from jug.tests.utils import simple_execute

Task = jug.task.Task
jug.task.Task.store = dict_store()
def _setup():
    jug.task.Task.store = dict_store()

def _teardown():
    jug.task.alltasks = []

task_reset = with_setup(_setup, _teardown)

def add1(x):
    return x + 1
def add2(x):
    return x + 2

def _assert_tsorted(tasks):
    from itertools import chain
    for i,ti in enumerate(tasks):
        for j,tj in enumerate(tasks[i+1:]):
            for dep in chain(ti.args, ti.kwargs.values()):
                if type(dep) is list:
                    assert tj not in dep
                else:
                    assert tj is not dep

@task_reset
def test_topological_sort():
    bases = [jug.task.Task(add1,i) for i in range(10)]
    derived = [jug.task.Task(add1,t) for t in bases]
    derived2 = [jug.task.Task(add1,t) for t in derived]
    derived3 = [jug.task.Task(add1,t) for t in derived]
    
    alltasks = bases + derived
    jug.task.topological_sort(alltasks)
    assert len(alltasks) == len(bases) + len(derived)
    _assert_tsorted(alltasks)
    
    alltasks.reverse()
    jug.task.topological_sort(alltasks)
    assert len(alltasks) == len(bases) + len(derived)
    _assert_tsorted(alltasks)

    alltasks = bases + derived
    alltasks.reverse()
    jug.task.topological_sort(alltasks)
    assert len(alltasks) == len(bases) + len(derived)
    _assert_tsorted(alltasks)

    alltasks = derived + bases
    jug.task.topological_sort(alltasks)
    assert len(alltasks) == len(bases) + len(derived)
    _assert_tsorted(alltasks)

    alltasks = derived + bases + derived2
    jug.task.topological_sort(alltasks)
    assert len(alltasks) == len(bases) + len(derived) + len(derived2)
    _assert_tsorted(alltasks)

    alltasks = derived + bases + derived2 + derived3
    jug.task.topological_sort(alltasks)
    assert len(alltasks) == len(bases) + len(derived) + len(derived2) + len(derived3)
    _assert_tsorted(alltasks)

@task_reset
def test_topological_sort_kwargs():
    def add2(x):
        return x + 2
    def sumlst(lst,param):
        return sum(lst)

    bases = [jug.task.Task(add2,x=i) for i in range(10)]
    derived = [jug.task.Task(sumlst,lst=bases,param=p) for p in range(4)]

    alltasks = bases + derived
    jug.task.topological_sort(alltasks)
    assert len(alltasks) == len(bases) + len(derived)
    _assert_tsorted(alltasks)
    
    alltasks.reverse()
    jug.task.topological_sort(alltasks)
    assert len(alltasks) == len(bases) + len(derived)
    _assert_tsorted(alltasks)

    alltasks = bases + derived
    alltasks.reverse()
    jug.task.topological_sort(alltasks)
    assert len(alltasks) == len(bases) + len(derived)
    _assert_tsorted(alltasks)

    alltasks = derived + bases
    jug.task.topological_sort(alltasks)
    assert len(alltasks) == len(bases) + len(derived)
    _assert_tsorted(alltasks)

def data():
    return list(range(20))
def mult(r,f):
    return [f*rr for rr in r]
def reduce(r):
    return sum(r)

@task_reset
def test_topological_sort_canrun():
    Task = jug.task.Task
    input = Task(data)
    for f in range(80):
        Task(reduce, Task(mult,input,f))

    alltasks = jug.task.alltasks
    jug.task.topological_sort(alltasks)
    assert len(alltasks) == len(set(t.hash() for t in alltasks))
    for t in alltasks:
        assert t.can_run()
        t.run()

@task_reset
def test_load_after_run():
    T = jug.task.Task(add1,1)
    T.run()
    assert T.can_load()

@task_reset
def test_hash_same_func():
    T0 = jug.task.Task(add1,0)
    T1 = jug.task.Task(add1,1)

    assert T0.hash() != T1.hash()
    
@task_reset
def test_hash_different_func():
    T0 = jug.task.Task(add1,0)
    T1 = jug.task.Task(add2,0)

    assert T0.hash() != T1.hash()


@task_reset
def test_taskgenerator():
    @jug.task.TaskGenerator
    def double(x):
        return 2*x
    T=double(2)
    assert type(T) == jug.task.Task


@task_reset
def test_unload():
    T0 = jug.task.Task(add1,0)
    assert not hasattr(T0, '_result')
    assert T0.can_run()
    T0.run()
    assert hasattr(T0, '_result')
    assert T0.result == 1
    T0.unload()
    assert T0.result == 1

@task_reset
def test_unload_recursive():
    T0 = jug.task.Task(add1,0)
    T1 = jug.task.Task(add1,T0)
    T2 = jug.task.Task(add1,T1)
    assert not hasattr(T0, '_result')
    T0.run()
    T1.run()
    T2.run()
    assert hasattr(T0, '_result')

    T2.unload_recursive()
    assert not hasattr(T0, '_result')

def identity(x):
    return x

@task_reset
def test_cachedfunction():
    assert jug.task.CachedFunction(identity,123) == 123
    assert jug.task.CachedFunction(identity,'mixture') == 'mixture'

@task_reset
def test_npyload():
    import numpy as np
    A = np.arange(23)
    assert np.all(jug.task.CachedFunction(identity,A) == A)

@jug.task.TaskGenerator
def double(x):
    return 2 * x

@task_reset
def test_value():
    two = double(1)
    four = double(two)
    eight = double(four)
    two.run()
    four.run()
    eight.run()
    assert jug.task.value(eight) == 8

@task_reset
def test_dict_sort_run():
    tasks = [double(1), double(2), Task(identity,2) ]
    tasks += [Task(identity,{ 'one' : tasks[2], 'two' : tasks[0], 'three' : { 1 : tasks[1], 0 : tasks[0] }})]
    jug.task.topological_sort(tasks)
    for t in tasks:
        assert t.can_run()
        t.run()
    assert tasks[-1].result == { 'one' : 2, 'two' : 2, 'three' : {1 : 4, 0: 2}}

@task_reset
def test_unload_recursive():
    two = double(1)
    four = double(two)
    two.run()
    four.run()
    four.unload_recursive ()
    assert not hasattr(four, '_result')
    assert not hasattr(two, '_result')

# Crashed in version 0.7.3
@task_reset
def test_unload_wnoresult():
    t = Task(add2, 3)
    t.unload()

@task_reset
def test_starts_unloaded():
    t = Task(add2, 3)
    assert not t.is_loaded()

@task_reset
def test__str__repr__():
    t = Task(add2, 3)
    assert str(t).find('add2') >= 0
    assert repr(t).find('add2') >= 0
    assert repr(t).find('3') >= 0


def add_tuple(a_b):
    a,b = a_b
    return a + b

@task_reset
def test_unload_recursive_tuple():
    T0 = jug.task.Task(add1,0)
    T1 = jug.task.Task(add1,T0)
    T2 = jug.task.Task(add_tuple,(T0,T1))
    T3 = jug.task.Task(add1, T2)
    assert not hasattr(T0, '_result')
    T0.run()
    T1.run()
    T2.run()
    T3.run()
    assert hasattr(T0, '_result')

    T3.unload_recursive()
    assert not hasattr(T0, '_result')

@task_reset
def test_builtin_function():
    import numpy as np
    store, space = jug.jug.init('jug/tests/jugfiles/builtin_function.py', 'dict_store')
    simple_execute()
    a8 = jug.task.value(space['a8'])
    assert np.all(a8 == np.arange(8))

########NEW FILE########
__FILENAME__ = test_utils_customhash
from jug.backends.dict_store import dict_store
from jug.tests.utils import simple_execute
from jug.tests.task_reset import task_reset
import jug.jug

@task_reset
def test_w_barrier():
    store, space = jug.jug.init('jug/tests/jugfiles/custom_hash_function.py', 'dict_store')
    simple_execute()
    assert space['hash_called']

########NEW FILE########
__FILENAME__ = test_utils_identity
from jug.utils import identity
from .task_reset import task_reset

@task_reset
def test_utils_identity():
    identity(2).run() == 2


########NEW FILE########
__FILENAME__ = test_utils_timed_path
from time import sleep
from os import system
from nose.tools import with_setup

import jug.utils
import jug.task                             
from jug.backends.dict_store import dict_store

def _remove_test_file():
    system("rm test_file")

@with_setup(teardown=_remove_test_file)
def test_util_timed_path():
    Task = jug.task.Task
    jug.task.Task.store = dict_store()
    system("touch test_file")
    t0 = jug.utils.timed_path('test_file')
    t1 = jug.utils.timed_path('test_file')
    assert t0.hash() == t1.hash()
    sleep(1.1)
    system("touch test_file")
    t1 = jug.utils.timed_path('test_file')
    assert t0.hash() != t1.hash()
    assert t0.run() == 'test_file'
    assert t1.run() == 'test_file'


########NEW FILE########
__FILENAME__ = test_webstatus
from jug.subcommands.webstatus import _format_counts

def test_format_counts():
    assert len(_format_counts({'n': 0}, {'n': 1}, {'n': 2}, {'n':3}))
    assert len(_format_counts(
                    {'n': 0, 'n2': 1 },
                    {'n': 1, 'n2': 0 },
                    {'n': 2, 'n2': 3 },
                    {'n': 3, 'n2': 4 }
                    ))

########NEW FILE########
__FILENAME__ = utils
from .task_reset import task_reset

def simple_execute():
    from jug.jug import execution_loop
    from jug.task import alltasks
    from jug.options import default_options
    from collections import defaultdict
    execution_loop(alltasks, default_options, defaultdict(int), defaultdict(int))

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
# Copyright (C) 2009-2014, Luis Pedro Coelho <luis@luispedro.org>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.


import os

from .task import Task, Tasklet, value

__all__ = [
    'timed_path',
    'identity',
    'CustomHash',
    ]

def _return_first(one, two):
    '''
    one = _return_first(one, two)

    Used internally to implement jug.util.timed_path
    '''
    return one

def timed_path(path):
    '''
    opath = timed_path(ipath)

    Returns a Task object that simply returns `path` with the exception that it uses the
    paths mtime (modification time) in the hash. Thus, if the file contents change, this triggers
    an invalidation of the results (which propagates).

    Parameters
    ----------
    ipath : str
        A filesystem path

    Returns
    -------
    opath : str
        A task equivalent to ``(lambda: ipath)``.
    '''
    mtime = os.stat_result(os.stat(path)).st_mtime
    return Task(_return_first, path, mtime)

def _identity(x):
    return x

def identity(x):
    '''
    x = identity(x)

    `identity` implements the identity function as a Task
    (i.e., value(identity(x)) == x)

    This seems pointless, but if x is, for example, a very large list, then
    using the output of this function might be much faster than using x directly.

    Parameters
    ----------
    x : any object

    Returns
    -------
    x : x
    '''
    if isinstance(x, (Task, Tasklet)):
        return x
    t = Task(_identity, x)
    t.name = 'identity'
    return t

class CustomHash(object):
    '''
    value = CustomHash(obj, hash_function)

    Set a custom hash function

    This is an advanced feature and you can shoot yourself in the foot with it.
    Make sure you know what you are doing. In particular, hash_function should
    be a strong hash: ``hash_function(obj0) == hash_function(obj1)`` is taken
    to imply that ``obj0 == obj1``

    Parameters
    ----------
    obj : any object
    hash_function : function
        This should take your object and return a str
    '''
    def __init__(self, obj, hash_function):
        self.obj = obj
        self.hash_function = hash_function

    def __jug_hash__(self):
        return self.hash_function(self.obj)

    def __jug_value__(self):
        return value(self.obj)

########NEW FILE########
__FILENAME__ = jugfile
from jug.task import Task, TaskGenerator
from time import sleep

@TaskGenerator
def compfeats(url):
    print('Feats called: {}'.format(url))
    sleep(2)
    return url+'feats'

@TaskGenerator
def nfold(param, feats):
    print('nfold called: {} {}'.format(param, feats))
    sleep(3)
    return param, feats

imgs = ['images/img1.png','images/img2.png']
feats = [compfeats(img) for img in imgs]
tenfold = [nfold(param=p,feats=feats) for p in range(10)]


########NEW FILE########
