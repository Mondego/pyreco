__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Pygr documentation build configuration file, created by
# sphinx-quickstart on Mon Jan 19 09:36:56 2009.
#
# This file is execfile()d with the current directory set
# to its containing dir.
#
# The contents of this file are pickled, so don't put values
# in the namespace that aren't pickleable (module imports are okay,
# they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import os
import sys

# need to insert the source pygr directory if we want to access modules
curr_dir = os.path.dirname(__file__)
pygr_root_dir = os.path.join(curr_dir, '..', '..')
sys.path.insert(0, pygr_root_dir)

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.

extensions = ['sphinx.ext.doctest', 'sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'contents'

# General substitutions.
project = 'Pygr DocTest'
copyright = '2009-2010, Pygr Team'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '0.8'
# The full version, including alpha/beta/rc tags.
release = '0.8.2'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

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
html_style = 'pygr-doc.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = None

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

# Content template for the index page.
html_index = 'index.html'

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}
html_sidebars = {'index': 'indexsidebar.html'}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}
html_additional_pages = {
    'index': 'index.html',
    'media': 'media.html',
}

# If false, no module index is generated.
#html_use_modindex = True

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.
#html_use_opensearch = False

# Output file base name for HTML help builder.
htmlhelp_basename = 'Pygrdoc'

# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class
# [howto/manual]).
latex_documents = [
  ('contents', 'Pygr.tex', 'Pygr Documentation', 'Chris Lee', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = slice_pickle_obj
class MySliceInfo(object):

    def __init__(self, id, start, stop, orientation):
        self.id = id
        self.start = start
        self.stop = stop
        self.orientation = orientation


class MyFunkySliceInfo(object):

    def __init__(self, seq_id, begin, end, strand):
        self.seq_id = seq_id
        self.begin = begin
        self.end = end
        self.strand = strand

########NEW FILE########
__FILENAME__ = annotation
from __future__ import generators
from sequence import *
import classutil
import UserDict
import weakref


def getAnnotationAttr(self, attr):
    'forward attributes from slice object if available'
    return self.db.getSliceAttr(self.db.sliceDB[self.id], attr)


def annotation_repr(self):
    if self.annotationType is not None:
        title = self.annotationType
    else:
        title = 'annot'
    if self.orientation > 0:
        return '%s%s[%d:%d]' % (title, self.id, self.start, self.stop)
    else:
        return '-%s%s[%d:%d]' % (title, self.id, -self.stop, -self.start)


class AnnotationSeqDescr(object):
    'get the sequence interval corresponding to this annotation'

    def __get__(self, obj, objtype):
        return absoluteSlice(obj._anno_seq, obj._anno_start,
                             obj._anno_start + obj.stop)


class AnnotationSliceDescr(object):
    'get the sequence interval corresponding to this annotation'

    def __get__(self, obj, objtype):
        return relativeSlice(obj.pathForward.sequence, obj.start, obj.stop)


class AnnotationSeqtypeDescr(object):
    'get seqtype of the sequence interval corresponding to this annotation'

    def __get__(self, obj, objtype):
        return obj._anno_seq.seqtype()


class AnnotationSeq(SeqPath):
    'base class representing an annotation'
    start = 0
    step = 1
    orientation = 1

    def __init__(self, id, db, parent, start, stop):
        self.id = id
        self.db = db
        self.stop = stop - start
        self._anno_seq = parent
        self._anno_start = start
        self.path = self

    __getattr__ = getAnnotationAttr
    sequence = AnnotationSeqDescr()
    annotationType = classutil.DBAttributeDescr('annotationType')
    _seqtype = AnnotationSeqtypeDescr()
    __repr__ = annotation_repr

    def __cmp__(self, other):
        if not isinstance(other, AnnotationSeq):
            return -1
        if cmp(self.sequence, other.sequence) == 0:
            if self.id == other.id and self.db is other.db:
                return cmp((self.start, self.stop), (other.start, other.stop))
        return NOT_ON_SAME_PATH

    def strslice(self, start, stop):
        raise ValueError('''this is an annotation, and you cannot get
                         a sequence string from it. Use its sequence attribute
                         to get a sequence object representing this interval.
                         ''')


class AnnotationSlice(SeqDBSlice):
    'represents subslice of an annotation'
    __getattr__=getAnnotationAttr
    sequence = AnnotationSliceDescr()
    annotationType = classutil.DBAttributeDescr('annotationType')
    __repr__ = annotation_repr


class TranslationAnnotSeqDescr(object):
    'get the sequence interval corresponding to this annotation'

    def __get__(self, obj, objtype):
        return absoluteSlice(obj._anno_seq, obj._anno_start, obj._anno_stop)


class TranslationAnnotFrameDescr(object):
    """Get the frame of this protein translation, relative to original DNA."""

    def __get__(self, obj, objtype):
        orig = obj.pathForward.sequence
        if orig.orientation > 0:
            frame = (orig.start % 3) + 1
        else:
            return -((orig.start + 1) % 3 + 1)
        return frame


class TranslationAnnot(AnnotationSeq):
    'annotation representing aa translation of a given nucleotide interval'

    def __init__(self, id, db, parent, start, stop):
        AnnotationSeq.__init__(self, id, db, parent, start, stop)
        self.stop /= 3
        self._anno_stop = stop
    sequence = TranslationAnnotSeqDescr()
    frame = TranslationAnnotFrameDescr()
    _seqtype = PROTEIN_SEQTYPE

    def strslice(self, start, stop):
        'get the aa translation of our associated ORF'
        try:
            aa = self._translation
        except AttributeError:
            aa = self._translation = translate_orf(str(self.sequence))
        return aa[start:stop]


class TranslationAnnotSliceDescr(object):
    'get the sequence interval corresponding to this annotation'

    def __get__(self, obj, objtype):
        return relativeSlice(obj.pathForward.sequence, 3 * obj.start,
                             3 * obj.stop)


class TranslationAnnotSlice(AnnotationSlice):
    sequence = TranslationAnnotSliceDescr()
    frame = TranslationAnnotFrameDescr()


class AnnotationDB(object, UserDict.DictMixin):
    'container of annotations as specific slices of db sequences'

    def __init__(self, sliceDB, seqDB, annotationType=None,
                 itemClass=AnnotationSeq,
                 itemSliceClass=AnnotationSlice,
                 itemAttrDict=None, # GET RID OF THIS BACKWARDS-COMPATIBILITY KLUGE!!
                 sliceAttrDict=None, maxCache=None, autoGC=True,
                 checkFirstID=True, **kwargs):
        '''sliceDB must map identifier to a sliceInfo object;
        sliceInfo must have attributes: id, start, stop, orientation;
        seqDB must map sequence ID to a sliceable sequence object;
        sliceAttrDict gives optional dict of item attributes that
        should be mapped to sliceDB item attributes.
        maxCache specfies the maximum number of annotation objects
        to keep in the cache.'''
        if autoGC: # automatically garbage collect unused objects
            self._weakValueDict = classutil.RecentValueDictionary(autoGC)
        else:
            self._weakValueDict = {} # object cache
        self.autoGC = autoGC
        if sliceAttrDict is None:
            sliceAttrDict = {}
        if sliceDB is not None:
            self.sliceDB = sliceDB
        else: # NEED TO CREATE / OPEN A DATABASE FOR THE USER
            self.sliceDB = classutil.get_shelve_or_dict(**kwargs)
        self.seqDB = seqDB
        self.annotationType = annotationType
        self.itemClass = itemClass
        self.itemSliceClass = itemSliceClass
        self.sliceAttrDict = sliceAttrDict # USER-PROVIDED ALIASES
        if maxCache is not None:
            self.maxCache = maxCache
        if checkFirstID:
            try: # don't cache anything now; schema may change itemClass!
                k = iter(self).next() # get the first ID if any
                self.get_annot_obj(k, self.sliceDB[k]) # valid annotation?
            except KeyError: # a convenient warning to the user...
                raise KeyError('''\
cannot create annotation object %s; sequence database %s may not be correct'''
                               % (k, repr(seqDB), ))
            except StopIteration:
                pass # dataset is empty so there is nothing we can check...
    __getstate__ = classutil.standard_getstate ############### PICKLING METHODS
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(sliceDB=0, seqDB=0, annotationType=0, autoGC=0,
                        itemClass=0, itemSliceClass=0, sliceAttrDict=0,
                        maxCache=0)

    def __hash__(self):                 # @CTB unnecessary??
        'ALLOW THIS OBJECT TO BE USED AS A KEY IN DICTS...'
        return id(self)

    def __getitem__(self, k):
        'get annotation object by its ID'
        try: # GET FROM OUR CACHE
            return self._weakValueDict[k]
        except KeyError:
            pass
        return self.sliceAnnotation(k, self.sliceDB[k])

    def __setitem__(self, k, v):
        raise KeyError('''you cannot save annotations directly using annoDB[k]
                       = v. Instead, use annoDB.new_annotation(k,sliceInfo)
                       where sliceInfo provides a sequence ID, start, stop (and
                       any additional info desired), and will be saved directly
                       to the sliceDB.''')

    def getSliceAttr(self, sliceInfo, attr):
        try:
            k = self.sliceAttrDict[attr] # USE ALIAS IF PROVIDED
        except KeyError:
            return getattr(sliceInfo, attr) # GET ATTRIBUTE AS USUAL
        try: # REMAP TO ANOTHER ATTRIBUTE NAME
            return getattr(sliceInfo, k)
        except TypeError: # TREAT AS int INDEX INTO A TUPLE
            return sliceInfo[k]

    def get_annot_obj(self, k, sliceInfo):
        'create an annotation object based on the input sliceInfo'
        start = int(self.getSliceAttr(sliceInfo, 'start'))
        stop = int(self.getSliceAttr(sliceInfo, 'stop'))

        try:
            orientation = self.getSliceAttr(sliceInfo, 'orientation')
            orientation = int(orientation)
            if orientation < 0 and start >= 0:
                start, stop = (-stop, -start) # Negative-orientation coords
        except (AttributeError, IndexError):
            pass                        # ok if no orientation is specified.

        if start >= stop:
            raise IndexError('annotation %s has zero or negative length \
                             [%s:%s]!' % (k, start, stop))
        seq_id = self.getSliceAttr(sliceInfo, 'id')
        seq = self.seqDB[seq_id]
        return self.itemClass(k, self, seq, start, stop)

    def sliceAnnotation(self, k, sliceInfo, limitCache=True):
        'create annotation and cache it'
        a = self.get_annot_obj(k, sliceInfo)
        try: # APPLY CACHE SIZE LIMIT IF ANY
            if limitCache and self.maxCache < len(self._weakValueDict):
                self._weakValueDict.clear()
        except AttributeError:
            pass
        self._weakValueDict[k] = a # CACHE THIS IN OUR DICT
        return a

    def new_annotation(self, k, sliceInfo):
        'save sliceInfo to the annotation database \
                and return annotation object'
        # First, check if it gives a valid annotation
        a = self.sliceAnnotation(k, sliceInfo)
        try:
            # Now, save it in the slice database
            self.sliceDB[k] = sliceInfo
        except:
            try:
                # Delete it from cache
                del self._weakValueDict[k]
            except:
                pass
            raise
        self._wroteSliceDB = True
        return a

    def foreignKey(self, attr, k):
        'iterate over items matching specified foreign key'
        for t in self.sliceDB.foreignKey(attr, k):
            try: # get from cache if exists
                yield self._weakValueDict[t.id]
            except KeyError:
                yield self.sliceAnnotation(t.id, t)

    def __contains__(self, k):
        return k in self.sliceDB

    def __len__(self):
        return len(self.sliceDB)

    def __iter__(self):
        return iter(self.sliceDB) ########## ITERATORS

    def  keys(self):
        return self.sliceDB.keys()

    def iteritems(self):
        'uses maxCache to manage caching of annotation objects'
        for k, sliceInfo in self.sliceDB.iteritems():
            yield k, self.sliceAnnotation(k, sliceInfo)

    def itervalues(self):
        'uses maxCache to manage caching of annotation objects'
        for k, v in self.iteritems():
            yield v

    def items(self):
        'forces load of all annotation objects into cache'
        return [(k, self.sliceAnnotation(k, sliceInfo, limitCache=False))
                for (k, sliceInfo) in self.sliceDB.items()]

    def values(self):
        'forces load of all annotation objects into cache'
        return [self.sliceAnnotation(k, sliceInfo, limitCache=False)
                for (k, sliceInfo) in self.sliceDB.items()]

    def add_homology(self, seq, search, id=None, idFormat='%s_%d',
                     autoIncrement=False, maxAnnot=999999,
                     maxLoss=None, sliceInfo=None, **kwargs):
        'find homology in our seq db and add as annotations'
        try: # ENSURE THAT sliceAttrDict COMPATIBLE WITH OUR TUPLE FORMAT
            if self.sliceAttrDict['id'] != 0:
                raise KeyError
        except KeyError:
            sliceAttrDict['id'] = 0 # USE TUPLE AS OUR INTERNAL STANDARD FORMAT
            sliceAttrDict['start'] = 1
            sliceAttrDict['stop'] = 2
        if autoIncrement:
            id = len(self.sliceDB)
        elif id is None:
            id = seq.id
        if isinstance(search, str): # GET SEARCH METHOD
            search = getattr(self.seqDB, search)
        if isinstance(seq, str): # CREATE A SEQ OBJECT
            seq = Sequence(seq, str(id))
        al = search(seq, **kwargs) # RUN THE HOMOLOGY SEARCH
        if maxLoss is not None: # REQUIRE HIT BE AT LEAST A CERTAIN LENGTH
            kwargs['minAlignSize'] = len(seq)-maxLoss
        hits = al[seq].keys(**kwargs) # OBTAIN LIST OF HIT INTERVALS
        if len(hits) > maxAnnot:
            raise ValueError('too many hits for %s: %d' % (id, len(hits)))
        out = []
        i = 0
        k = id
        for ival in hits: # CREATE ANNOTATION FOR EACH HIT
            if len(hits)>1: # NEED TO CREATE AN ID FOR EACH HIT
                if autoIncrement:
                    k = len(self.sliceDB)
                else:
                    k = idFormat % (id, i)
                i += 1
            if sliceInfo is not None: # SAVE SLICE AS TUPLE WITH INFO
                a = self.new_annotation(k, (ival.id, ival.start, ival.stop)
                                        + sliceInfo)
            else:
                a = self.new_annotation(k, (ival.id, ival.start, ival.stop))
            out.append(a) # RETURN THE ANNOTATION
        return out

    def close(self):
        'if sliceDB needs to be closed, do it and return True, otherwise False'
        try:
            if self._wroteSliceDB:
                self.sliceDB.close()
                self._wroteSliceDB = False # DISK FILE IS UP TO DATE
                return True
        except AttributeError:
            pass
        return False

    def __del__(self):
        if self.close():
            import sys
            print >>sys.stderr, '''
WARNING: you forgot to call AnnotationDB.close() after writing
new annotation data to it.  This could result in failure to properly
store the data in the associated disk file.  To avoid this, we
have automatically called AnnotationDB.sliceDB.close() to write the data
for you, when the AnnotationDB was deleted.'''

    def clear_cache(self):
        'empty the cache'
        self._weakValueDict.clear()

    # not clear what this should do for AnnotationDB

    def copy(self):
        raise NotImplementedError("nonsensical in AnnotationDB")

    def setdefault(self, k, d=None):
        raise NotImplementedError("nonsensical in AnnotationDB")

    def update(self, other):
        raise NotImplementedError("nonsensical in AnnotationDB")

    # these methods should not be implemented for read-only database.

    def clear(self):
        raise NotImplementedError("no deletions allowed")

    def pop(self):
        raise NotImplementedError("no deletions allowed")

    def popitem(self):
        raise NotImplementedError("no deletions allowed")


class AnnotationServer(AnnotationDB):
    'XMLRPC-ready server for AnnotationDB'
    xmlrpc_methods={'get_slice_tuple': 0, 'get_slice_items': 0,
                    'get_annotation_attr': 0, 'keys': 0,
                    '__len__': 0, '__contains__': 0}

    def get_slice_tuple(self, k):
        'get (seqID,start,stop) for a given key'
        try:
            sliceInfo = self.sliceDB[k]
        except KeyError:
            return '' # XMLRPC-acceptable failure code
        start = int(self.getSliceAttr(sliceInfo, 'start'))
        stop = int(self.getSliceAttr(sliceInfo, 'stop'))
        try:
            if int(self.getSliceAttr(sliceInfo, 'orientation')) < 0 \
               and start >= 0:
                start, stop = (-stop, -start) # Negative-orientation coords
        except AttributeError:
            pass
        return (self.getSliceAttr(sliceInfo, 'id'), start, stop)

    def get_slice_items(self):
        'get all (key,tuple) pairs in one query'
        l = []
        for k in self.sliceDB:
            l.append((k, self.get_slice_tuple(k)))
        return l

    def get_annotation_attr(self, k, attr):
        'get the requested attribute of the requested key'
        try:
            sliceInfo = self.sliceDB[k]
        except KeyError:
            return ''
        try:
            return self.getSliceAttr(sliceInfo, attr)
        except AttributeError:
            return ''


class AnnotationClientSliceDB(dict):
    'proxy just queries the server'

    def __init__(self, db):
        self.db = db
        dict.__init__(self)

    def __getitem__(self, k):
        try:
            return dict.__getitem__(self, k)
        except KeyError:
            t = self.db.server.get_slice_tuple(k)
            if t == '':
                raise KeyError('no such annotation: ' + str(k))
            dict.__setitem__(self, k, t)
            return t

    def __setitem__(self, k, v):
        raise ValueError('XMLRPC client is read-only')

    def keys(self):
        return self.db.server.keys()

    def __iter__(self):
        return iter(self.keys())

    def items(self):
        return self.db.server.get_slice_items()

    def iteritems(self):
        return iter(self.items())

    def __len__(self):
        return self.db.server.__len__()

    def __contains__(self, k):
        return self.db.server.__contains__(k)


class AnnotationClient(AnnotationDB):
    'XMLRPC AnnotationDB client'

    def __init__(self, url, name, seqDB, itemClass=AnnotationSeq,
                 itemSliceClass=AnnotationSlice, autoGC=True, **kwargs):
        if autoGC: # automatically garbage collect unused objects
            self._weakValueDict = classutil.RecentValueDictionary(autoGC)
        else:
            self._weakValueDict = {} # object cache
        self.autoGC = autoGC
        import coordinator
        self.server = coordinator.get_connection(url, name)
        self.url = url
        self.name = name
        self.seqDB = seqDB
        self.sliceDB = AnnotationClientSliceDB(self)
        self.itemClass = itemClass
        self.itemSliceClass = itemSliceClass

    def __getstate__(self):
        return dict(url=self.url, name=self.name, seqDB=self.seqDB,
                    autoGC=self.autoGC)

    def getSliceAttr(self, sliceInfo, attr):
        if attr=='id':
            return sliceInfo[0]
        elif attr=='start':
            return sliceInfo[1]
        elif attr=='stop':
            return sliceInfo[2]
        elif attr=='orientation':
            raise AttributeError('ori not saved')
        else:
            v = self.server.get_annotation_attr(sliceInfo[0], attr)
            if v=='':
                raise AttributeError('this annotation has no attr: ' + attr)
            return v

########NEW FILE########
__FILENAME__ = catalog_downloads


def catalog_downloads(url, fileFilter, fileNamer, fileDocumenter, klass):
    '''returns dict of resources for downloading target data:
    url: URL to a directory that gives links to the desired data
    fileFilter: function that returns True for a desired file name
    fileNamer: function that converts a file name into desired key value
    fileDocumenter: function that returns a docstring based on file name
    klass: a Python class or function that takes file URL as a single argument,
           and returns value to store in dictionary

    example usage:
    d = catalog_downloads("http://biodb.bioinformatics.ucla.edu/PYGRDATA/",
                          lambda x: x.endswith(".txt.gz"),
                          lambda x: "Bio.MSA.UCSC."+x[:-3],
                          SourceURL)
    '''
    import formatter
    import htmllib
    import urllib
    #from BeautifulSoup import BeautifulSoup
    ifile = urllib.urlopen(url)
    try:
        p = htmllib.HTMLParser(formatter.NullFormatter())
        p.feed(ifile.read())
        l = p.anchorlist
        #soup = BeautifulSoup(ifile.read())
        # l = [str(a['href']) for a in soup.findAll('a')]
    finally:
        ifile.close()
    d = {}
    if url[-1] != '/': # make sure url ends in trailing /
        url += '/'
    for s in l: # find all anchors in the document
        if fileFilter(s): # save it
            o = klass(urllib.basejoin(url, s))
            o.__doc__ = fileDocumenter(s)
            d[fileNamer(s)] = o
    return d


def save_NLMSA_downloaders(url, fileFilter=lambda x: x.endswith(".txt.gz"),
                           resourceStem='Bio.MSA.UCSC.',
                           fileDocumenter=None, fileNamer=None):
    '''save NLMSA downloader / builder objects for a set
    of downloadable textdump files'''
    if fileDocumenter is None:
        fileDocumenter = lambda x: 'NLMSA alignment ' + x
    if fileNamer is None: # a default resource naming function
        fileNamer = lambda x: resourceStem + x[:-3] # remove .gz suffix
    from pygr.nlmsa_utils import NLMSABuilder
    from pygr.downloader import SourceURL
    d = catalog_downloads(url, fileFilter, fileNamer,
                          fileDocumenter, SourceURL)
    for resID, o in d.items():
        nlmsa = NLMSABuilder(o)
        nlmsa.__doc__ = fileDocumenter(resID)
        d[resID[:-4]] = nlmsa # remove .txt suffix
    from pygr import worldbase
    worldbase.add_resource(d)
    worldbase.commit()
    return d # just in case the user wants to see what was saved

########NEW FILE########
__FILENAME__ = leelabdb
import MySQLdb
import os
from splicegraph import *


spliceCalcs={'HUMAN_SPLICE_03':
             TableGroup(db='HUMAN_SPLICE_03', suffix='JUN03',
                        clusters='cluster_JUN03', exons='exon_formJUN03',
                        splices='splice_verification_JUN03',
                        genomic='genomic_cluster_JUN03', mrna='mrna_seqJUN03',
                        protein='protein_seqJUN03'),
             'HUMAN_SPLICE':
             TableGroup(db='HUMAN_SPLICE', suffix='jan02',
                        clusters='cluster_jan02',
                        exons='HUMAN_ISOFORMS.exon_form_4',
                        splices='splice_verification_jan02',
                        genomic='genomic_cluster_jan02',
                        mrna='HUMAN_ISOFORMS.mrna_seq_4',
                        protein='HUMAN_ISOFORMS.protein_seq_4'),
             'MOUSE_SPLICE':
             TableGroup(db='MOUSE_SPLICE', suffix='jan02',
                        clusters='cluster_jan02',
                        exons='MOUSE_ISOFORMS.exon_form_2',
                        splices='splice_verification_jan02',
                        genomic='genomic_cluster_jan02',
                        mrna='MOUSE_ISOFORMS.mrna_seq_2',
                        protein='MOUSE_ISOFORMS.protein_seq_2'),
             'MOUSE_SPLICE_03':
             TableGroup(db='MOUSE_SPLICE_03', suffix='JUN03',
                        clusters='cluster_JUN03', exons='exon_formJUN03',
                        splices='splice_verification_JUN03',
                        genomic='genomic_cluster_JUN03', mrna='mrna_seqJUN03',
                        protein='protein_seqJUN03')}


def getUserCursor(db):
    'get a cursor as the current user'
    db = MySQLdb.connect(db=db, read_default_file=os.environ['HOME']
                         + '/.my.cnf', compress=True)
    return db.cursor()


def getSpliceGraphFromDB(dbgroup, loadAll=False):
    """load data from MySQL using the designated database table group.
    If loadAll true, then load the entire splice graph into memory."""
    cursor = getUserCursor(dbgroup.db)
    import sys
    print >>sys.stderr, 'Reading database schema...'
    idDict = {}
    tables = describeDBTables(dbgroup.db, cursor, idDict)
    if hasattr(dbgroup, 'suffix'):
        # Get a set of tables ending in specified suffix
        # and create an index of their primary keys
        tables = suffixSubset(tables, dbgroup.suffix)
        idDict = indexIDs(tables)
    for t in dbgroup.values():
        # This table comes from another database...
        if t is not None and '.' in t and t not in tables:
            tables[t]=SQLTable(t, cursor) # ...so get it from there

    # LOAD DATA & BUILD THE SPLICE GRAPH
    return loadSpliceGraph(tables, dbgroup.clusters, dbgroup.exons,
                           dbgroup.splices, dbgroup.genomic, dbgroup.mrna,
                           dbgroup.protein, loadAll)


def localCopy(localFile, cpCommand):
    'if not already present on local file location, run cpCommand'
    if not os.access(localFile, os.R_OK):
        cmd=cpCommand % localFile
        print 'copying data:', cmd
        exit_code=os.system(cmd)
        if exit_code!=0:
            raise OSError((exit_code, 'command failed: %s' % cmd))
    return localFile

########NEW FILE########
__FILENAME__ = maf2nclist
from pygr.cnestedlist import *
from specialseq import *


def maf2nclist(maffiles, stem):
    align = NLMSALetters(stem, 'w')
    seqs = {}
    for i in maffiles:
        f = open(i, 'r')
        if f.readline().split()[0] != '##maf':
            raise "Error processing %s: Invalid file format" % (i)

        l = f.readline()
        while l:
##            print l
            la = l.split()
            if(len(la) == 0 or la[0] == '#'):
                pass
            elif(la[0] == 'a'):
                storeMAFrecord(align, seqs, f)
            else:
                return
            l=f.readline()
    align.build()
    return align


def storeMAFrecord(align, seqs, fh):
    s = fh.readline().split()
    begin = align.seqlist[0].length
    while len(s) == 7 and s[0] == 's':
##        print s
        lpoStart = begin
        seqStart = int(s[2])
        try:
            seq = seqs[s[1]]
        except:
            seq = refSequence(s[1])
            seqs[s[1]] = seq
        if (s[4] == '-'):
            rev = True
        else:
            rev = False
        for ival in s[6].split('-'):
            if len(ival) > 0:
                if (rev):
                    align[-(lpoStart + len(ival)):-lpoStart] = \
                            seq[seqStart:seqStart + len(ival)]
                else:
                    align[lpoStart:lpoStart + len(ival)] = \
                            seq[seqStart:seqStart + len(ival)]
            seqStart += len(ival)
            lpoStart += len(ival) + 1
        s = fh.readline().split()


maf2nclist(['chrX.maf', ], 'testdb/chrX')

########NEW FILE########
__FILENAME__ = maf2VSgraph
from __future__ import generators
from seqref import *
from pygr.seqdb import *
import string


def refIntervals(s):
    begin = 0
    gaps = 0

    end = 0
    for end in range(len(s)):
        if (s[end] == '-'):
            if (begin < end):
                yield (begin, end, begin - gaps, end - gaps, s[begin:end])
            begin = end + 1
            gaps += 1
    if end == 0:
        return
    end = end + 1
    if (begin < end):
        yield (begin, end, begin - gaps, end - gaps, s[begin:end])


def reverse_complement(s):
    compl={'a': 't', 'c': 'g', 'g': 'c', 't': 'a', 'u': 'a', 'n': 'n',
           'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A', 'U': 'A', 'N': 'N'}
    return ''.join([compl.get(c, c) for c in s[::-1]])


class MafParser:
    """
    Parses .maf files as defined by the Haussler dataset. The results
    of parsing are available as pathmapping between the sequences
    in the alignment. The sequences themselves are assumed unknown
    and use AnonSequence class.
    """
    options = {}

    def __init__(self, vbase=''):
        self.mAlign = PathMapping()
        self.sequences = {}
        self.vbase = vbase
        self._vid = 0

    def setpar(self, arry):
        """internal function """
        for p in arry:
            (key, value) = p.split('=')
            self.options[key] = value

    def readalign(self, opt, fh):
        """internal function parses alignment record from .maf file"""
##        print "entering readalign:", opt
        edgeInfo = {}
        for p in opt:
            (key, value) = p.split('=')
            edgeInfo[key] = value

        s = fh.readline().split()
##        print s;
        if(len(s) == 7 and s[0] == 's'):
            vseq = self._vseq(len(s[6]))
            self.mAlign += vseq
        while len(s) == 7 and s[0] == 's':
            # Add the sequence name to the dictionary,
            # then add a corresponding node to the mapping.
            if s[1] not in self.sequences:
                self.sequences[s[1]] = AnonSequence(int(s[5]), s[1])
                self.mAlign += self.sequences[s[1]]

            # PROCESS THE KNOWN INTERVALS
            if(s[4] == '-'):
                ns = self.sequences[s[1]][-int(s[2]):-int(s[2]) - int(s[3])]
                self.sequences[s[1]].seqsplice(reverse_complement(
                    s[6].replace('-', '')), ns.start, ns.stop)
            else:
                ns = self.sequences[s[1]][int(s[2]):int(s[2]) + int(s[3])]
                self.sequences[s[1]].seqsplice(s[6].replace('-', ''),
                                               ns.start, ns.stop)

            for inter in refIntervals(s[6]):
                self.mAlign[vseq[inter[0]:inter[1]]][ns[inter[2]:inter[3]]] = \
                        (inter[4])
                self.mAlign[ns[inter[2]:inter[3]]][vseq[inter[0]:inter[1]]] = \
                        (inter[4])

            s = fh.readline().split()

    def parse(self, filehandle):
        """parses the .maf filehandle """
        l = filehandle.readline()
        if l.split()[0] != '##maf':
            return
        else:
            self.setpar(l.split()[1:])

        l=filehandle.readline()
        while l:
            la = l.split()
##            print la
            if(len(la)==0 or la[0]=='#'):
##                print "skipping"
                1
            elif(la[0]=='a'):
##                print "reading alignment"
                self.readalign(la[1:], filehandle)
            else:
##                print "end of records"
                return

            l=filehandle.readline()

    def _vseq(self, slen):
        alen = len(string.letters)
        uid = self.vbase
        cum = self._vid
        while cum / alen > 0:
            uid += string.letters[cum % alen]
            cum /= alen
        uid += string.letters[cum % alen]
        self._vid += 1
        return AnonSequence(slen, uid)

    def _dump(self, alignTab, sequenceTab=None):
        for row in self.mAlign.repr_dict():
            alignTab.write('\t'.join(map(lambda x: str(x), row.values()))
                           + '\n')

        if(sequenceTab):
            for s in self.sequences.values():
                for inter in s.known_int():
                    sequenceTab.write('\t'.join(map(lambda x: str(x),
                                                    inter.values())) + '\n')

        del self.mAlign
        del self.sequences
        self.mAlign = PathMapping()
        self.sequences = {}

    def parseIntoDB(self, filehandle, cursor, alignTab, sequenceTab=None,
                    update=None):
        """parses the .maf filehandle into database using cursors"""
        c = filehandle.tell()
        filehandle.seek(0, 2)
        filesize = filehandle.tell()
        filehandle.seek(c)
        l = filehandle.readline()
        rc = 0
        count = 0
        if l.split()[0] != '##maf':
            return
        else:
            self.setpar(l.split()[1:])

        l=filehandle.readline()
        while l:
            la = l.split()
##            print la
            if(len(la)==0 or la[0]=='#'):
##                print "skipping"
                1
            elif(la[0]=='a'):
##                print "reading alignment"
                count+=1
                self.readalign(la[1:], filehandle)
                self._dump(alignTab, sequenceTab)
                if(update and not count % 1000):
                    cursor.execute(update % (int(filehandle.tell() * 100.
                                                 / filesize)))
            else:
##                print "end of records"
                return
            l=filehandle.readline()

########NEW FILE########
__FILENAME__ = seqref
from __future__ import generators
from pygr.sequence import *
#from pathquery import *


class AnonSequence(Sequence):
    """Defines a sequence class with unknown sequence, but
    known length"""

    def __init__(self, length, id):
        s = ''
        self.known = list()
        Sequence.__init__(self, s, id)
        self.stop = length

    def seqsplice(self, s, start, end):
        (begin, stop, step) = slice(start, end).indices(self.stop)

        if (start < end):
            self.known += [(s, start, stop)]
        elif start > end:
            self.known += [(s[::-1], start, stop)]

    def known_int(self):
        for u in self.known:
            yield {'src_id': self.id, 'start': u[1], 'end': u[2], 'seq': u[0]}


class ReferenceSequence(Sequence):
    """Defines a reference sequence class that is subscriptable
    by other sequences. If sequence ids match the resulting sequnce
    will reference this class. This is useful for coordinate
    transforms when an unknown sequence intervals are transformed
    to known sequence"""

    def __init__(self, s, id):
        Sequence.__init__(self, s, id)

    def __getitem__(self, iv):
        if(isinstance(iv, SeqPath)):
            if(iv.id == self.id):
                s = self[iv.start:iv.stop:iv.step]
                s.orientation = iv.orientation
                return s
        else:
            return SeqPath.__getitem__(self, iv)

    def mapCoordinates(self, obj):
        m = PathMapping2()
        for ival in obj:
            m[ival] = self[ival]
        return m


class UnkSequence(SeqPath):
    """Defines a sequence class for pure interval manipulation.
    No sequence information (i.e. length, or seq itself) is needed.
    """

    def __init__(self, id, start=0, end=0, step=1, orientation=1):
        self.id = id
        SeqPath.__init__(self, id)
        self.start = start
        self.stop = end
        self.step = step
        self.orientation = orientation
        if (self.start is not None and self.stop is not None
           and self.start > self.stop):
            t = self.start
            if (self.stop >= 0):
                self.start = self.stop + 1
            else:
                self.start = self.stop
            if (t >= 0):
                self.stop = t + 1
            else:
                self.stop = t
            self.orientation = -self.orientation

    def __getitem__(self, k):
        if isinstance(k, types.SliceType):
            (start, stop, step) = (k.start, k.stop, k.step)
            if k.step == None:
                step = 1
        elif isinstance(k, types.IntType):
            start = k
            stop = k + 1
            if (k == -1):
                stop = None
            step = 1
            return self[start:stop:step]
        else:
            raise KeyError('requires a slice object or integer key')
        if self.step == 1 and stop != None:
            return UnkSequence(self.id, self.start + start * self.step,
                           self.start + stop * self.step,
                           self.step * step, self.orientation)
        else:
            return UnkSequence(self.id, start, stop, step, self.orientation)

########NEW FILE########
__FILENAME__ = splicegraph
from pygr.sqlgraph import *
from pygr.sequence import *
from pygr.seqdb import *


def buildClusterSpliceGraph(c, alt5, alt3):
    """use exon/splice start and end positions to build splice graph
    for a cluster c. Also finds exons that share same start (but differ
    at end: alt5), or share the same end (but differ at start: alt3)."""
    start = {}
    end = {}
    none = []
    for e in c.exons:
        if e.genomic_start not in start:
            start[e.genomic_start] = []
        start[e.genomic_start].append(e)
        if e.genomic_end not in end:
            end[e.genomic_end] = []
        end[e.genomic_end].append(e)
    for s in c.splices:
        try:
            exons1 = end[s.ver_gen_start]
        except KeyError:
            exons1 = none
        try:
            exons2 = start[s.ver_gen_end]
        except KeyError:
            exons2 = none
        for e1 in exons1:
            for e2 in exons2:
                e1.next[e2] = s # SAVE SPLICE AS EDGE INFO...
                s.exons = (e1, e2) # SAVE EXONS DIRECTLY ON THE SPLICE OBJECT
    for exons in start.values():
        for e1 in exons:
            for e2 in exons:
                if e1 != e2:
                    alt5 += e1
                    alt5 += e2
                    e1.alt5 += e2
                    e2.alt5 += e1
    for exons in end.values():
        for e1 in exons:
            for e2 in exons:
                if e1 != e2:
                    alt3 += e1
                    alt3 += e2
                    e1.alt3 += e2
                    e2.alt3 += e1


def loadCluster(c, exon_forms, splices, clusterExons, clusterSplices,
                spliceGraph, alt5, alt3):
    """Loads data for a single cluster, and builds it into a splice graph."""
    clusterExons += c
    clusterSplices += c
    for e in exon_forms.select('where cluster_id=%s', (c.id, )):
        c.exons += e
        spliceGraph += e
    for s in splices.select('where cluster_id=%s', (c.id, )):
        c.splices += s
    buildClusterSpliceGraph(c, alt5, alt3)


class ExonForm(TupleO, SeqPath): # ADD ATTRIBUTES STORING SCHEMA INFO

    def __init__(self, t):
        TupleO.__init__(self, t) # 1ST INITIALIZE ATTRIBUTE ACCESS
        SeqPath.__init__(self, g[self.cluster_id], # INITIALIZE AS SEQ INTERVAL
                         self.genomic_start - 1, self.genomic_end)

    def __getattr__(self, attr):
        'both parent classes have getattr, so have to call them both...'
        try:
            return TupleO.__getattr__(self, attr)
        except AttributeError:
            return SeqPath.__getattr__(self, attr)


class Splice(TupleO):
    pass


def loadSpliceGraph(jun03, cluster_t, exon_t, splice_t, genomic_seq_t,
                    mrna_seq_t=None, protein_seq_t=None, loadAll=True):
    """
    Build a splice graph from the specified SQL tables representing gene
    clusters, exon forms, and splices. Each table must be specified
    as a DB.TABLENAME string.
    These tables are loaded into memory.
    The splice graph is built based on exact match of exon and splice ends.
    In addition, also builds alt5Graph (exons that match at start but differ
    at end) and alt3Graph (exons that match at end but differ at start).

    Loads all cluster, exon and splice data if loadAll is True.

    Returns tuple: clusters, exons, splices, spliceGraph, alt5Graph, alt3Graph
    """

    # CREATE OUR GRAPHS
    clusterExons = dictGraph()
    clusterSplices = dictGraph()
    spliceGraph = dictGraph()
    alt5 = dictGraph()
    alt3 = dictGraph()

    class YiGenomicSequence(DNASQLSequence):

        def __len__(self):
            return self._select('length(seq)')  # USE SEQ LENGTH FROM DATABASE

    g = jun03[genomic_seq_t]
    # Force genomic seq table to use transparent access
    g.objclass(YiGenomicSequence)

    # Only process this if provided an mRNA table by the user.
    if mrna_seq_t is not None:
        mrna = jun03[mrna_seq_t]
        # Force mRNA seq table to use transparent access.
        mrna.objclass(SQLSequence)
    else:
        mrna = None

    # Only process this if provided a protein table by the user.
    if protein_seq_t is not None:

        class YiProteinSQLSequence(ProteinSQLSequence):

            def __len__(self):
                return self.protein_length # USE SEQ LENGTH FROM DATABASE

        protein = jun03[protein_seq_t]
        # Force protein seq table to use transparent access
        protein.objclass(YiProteinSQLSequence)
        # Alias 'protein_seq' to appear as 'seq'
        protein.addAttrAlias(seq='protein_seq')
    else:
        protein = None

    exon_forms = jun03[exon_t]
    ExonForm.__class_schema__ = SchemaDict(((spliceGraph, 'next'),
                                            (alt5, 'alt5'), (alt3, 'alt3')))
    # Bind this class to container as the one to use as "row objects".
    exon_forms.objclass(ExonForm)

    if loadAll:
        print 'Loading %s...' % exon_forms
        exon_forms.load(ExonForm)

    clusters = jun03[cluster_t]

    class Cluster(TupleO):
        __class_schema__ = SchemaDict(((clusterExons, 'exons'),
                                       (clusterSplices, 'splices')))
    # Bind this class to container as the one to use as "row objects".
    clusters.objclass(Cluster)
    if loadAll:
        print 'Loading %s...' % clusters
        clusters.load(Cluster)

    splices = jun03[splice_t]
    # Bind this class to container as the one to use as "row objects".
    splices.objclass(Splice)
    if loadAll:
        print 'Loading %s...' % splices
        splices.load(Splice)

##     print 'Saving alignment of protein to mrna isoforms...'
##     mrna_protein=PathMapping2()
##     for form_id in protein:
##         p=protein[form_id]
##         m=mrna[form_id]
##         start=3*(p.mRNA_start-1)+int(p.reading_frame)
##         end=start+3*p.protein_length
##         mrna_protein[p]=m[start:end]

        print 'Adding clusters to graph...'
        for c in clusters.values(): # ADD CLUSTERS AS NODES TO GRAPH
            clusterExons+=c
            clusterSplices+=c

        print 'Adding exons to graph...'
        for e in exon_forms.values():
            c=clusters[e.cluster_id]
            try:
                c.exons+=e
                spliceGraph+=e
            except IndexError:
                pass # BAD EXON: EMPTY SEQUENCE INTERVAL... IGNORE IT

        print 'Adding splices to graph...'
        for s in splices.values():
            try:
                c=clusters[s.cluster_id]
            except KeyError: # WIERD, ONE SPLICE WITH BLANK (NOT NULL) VALUE!
                pass
            else:
                c.splices+=s

        print 'Building splice graph...'
        for c in clusters.values():
            buildClusterSpliceGraph(c, alt5, alt3)

    return clusters, exon_forms, splices, g, spliceGraph, alt5, alt3, mrna,\
            protein, clusterExons, clusterSplices

########NEW FILE########
__FILENAME__ = ucsc_ensembl_annot
import UserDict

from pygr import annotation, seqdb, sequence, sqlgraph, worldbase
from pygr.classutil import read_only_error


class UCSCStrandDescr(object):

    def __get__(self, obj, objtype):
        if obj.strand == '+':
            return 1
        else:
            return -1


class UCSCSeqIntervalRow(sqlgraph.TupleO):
    orientation = UCSCStrandDescr()


class UCSCEnsemblInterface(object):
    'package of gene, transcript, exon, protein interfaces to UCSC/Ensembl'

    def __init__(self, ucsc_genome_name, ens_species=None,
                 ucsc_serverInfo=None, ens_serverInfo=None,
                 ens_db=None, trackVersion='hgFixed.trackVersion'):
        '''Construct interfaces to UCSC/Ensembl annotation databases.
        ucsc_genome_name must be a worldbase ID specifying a UCSC genome.
        naming convention.
        ens_species should be the Ensembl database name (generally
        the name of the species).  If not specified, we will try
        to autodetect it based on ucsc_genome_name.
        The interface uses the standard UCSC and Ensembl mysql servers
        by default, unless you provide serverInfo argument(s).
        trackVersion must be the fully qualified MySQL table name
        of the trackVersion table containing information about the
        Ensembl version that each genome dataset connects to.'''
        # Connect to both servers and prepare database names.
        if ucsc_serverInfo is not None:
            if isinstance(ucsc_serverInfo, str): # treat as worldbase ID
                self.ucsc_server = worldbase(ucsc_serverInfo)
            else:
                self.ucsc_server = ucsc_serverInfo
        else:
            self.ucsc_server = sqlgraph.DBServerInfo(
                host='genome-mysql.cse.ucsc.edu', user='genome')
        if ens_serverInfo is not None:
            if isinstance(ens_serverInfo, str): # treat as worldbase ID
                self.ens_server = worldbase(ens_serverInfo)
            else:
                self.ens_server = ens_serverInfo
        else:
            self.ens_server = sqlgraph.DBServerInfo(
                host='ensembldb.ensembl.org', port=5306, user='anonymous')
        self.ucsc_db = ucsc_genome_name.split('.')[-1]
        if ens_db is None: # auto-set ensembl database name
            self.ens_db = self.get_ensembl_db_name(ens_species,
                                                   trackVersion)
        else:
            self.ens_db = ens_db
        # Connect to all the necessary tables.
        self.ucsc_ensGene_trans = sqlgraph.SQLTable('%s.ensGene' %
                   self.ucsc_db, serverInfo=self.ucsc_server,
                   primaryKey='name', itemClass=UCSCSeqIntervalRow)
        self.ucsc_ensGene_gene = sqlgraph.SQLTable('%s.ensGene' %
                   self.ucsc_db, serverInfo=self.ucsc_server,
                   primaryKey='name2', allowNonUniqueID=True,
                   itemClass=UCSCSeqIntervalRow,
                   attrAlias=dict(minTxStart='min(txStart)',
                                  maxTxEnd='max(txEnd)'))
        self.ucsc_ensGtp_gene = sqlgraph.SQLTable('%s.ensGtp' %
                   self.ucsc_db, serverInfo=self.ucsc_server,
                   primaryKey='gene', allowNonUniqueID=True)
        self.prot_db = sqlgraph.SQLTable('%s.ensGtp' % self.ucsc_db,
                                         serverInfo=self.ucsc_server,
                                         primaryKey='protein',
                                         itemClass=EnsemblProteinRow)
        self.prot_db.gRes = self
        self.ucsc_ensPep = sqlgraph.SQLTable('%s.ensPep' % self.ucsc_db,
                   serverInfo=self.ucsc_server,
                   itemClass=sqlgraph.ProteinSQLSequenceCached,
                   itemSliceClass=seqdb.SeqDBSlice)
        self.ens_exon_stable_id = sqlgraph.SQLTable('%s.exon_stable_id' %
                   self.ens_db, serverInfo=self.ens_server,
                   primaryKey='stable_id')
        self.ens_transcript_stable_id = sqlgraph.SQLTable(
                   '%s.transcript_stable_id' % self.ens_db,
                   serverInfo=self.ens_server, primaryKey='stable_id')
        # We will need this too.
        self.genome_seq = worldbase(ucsc_genome_name)
        # Finally, initialise all UCSC-Ensembl databases.
        self.trans_db = annotation.AnnotationDB(self.ucsc_ensGene_trans,
                                                self.genome_seq,
                                                checkFirstID=False,
                                                sliceAttrDict=dict(
                                                    id='chrom',
                                                    start='txStart',
                                                    stop='txEnd'),
                                      itemClass=EnsemblTranscriptAnnotationSeq)
        self.gene_db = annotation.AnnotationDB(self.ucsc_ensGene_gene,
                                               self.genome_seq,
                                               checkFirstID=False,
                                               sliceAttrDict=dict(
                                                   id='chrom',
                                                   start='txStart',
                                                   stop='txEnd'))
        exon_slicedb = EnsemblExonOnDemandSliceDB(self)
        self.exon_db = annotation.AnnotationDB(exon_slicedb,
                                               self.genome_seq,
                                               checkFirstID=False,
                                               sliceAttrDict=dict(id=0,
                                                 start=1, stop=2,
                                                 orientation=3))
        # Mappings.
        self.protein_transcript_id_map = sqlgraph.MapView(
            self.prot_db, self.trans_db,
            'select transcript from %s.ensGtp \
            where protein=%%s' % self.ucsc_db, inverseSQL='select protein \
            from %s.ensGtp where transcript=%%s' % self.ucsc_db,
            serverInfo=self.ucsc_server)
        self.transcripts_in_genes_map = sqlgraph.GraphView(
            self.gene_db, self.trans_db,
            "select transcript from %s.ensGtp where gene=%%s" % self.ucsc_db,
            inverseSQL="select gene from %s.ensGtp where transcript=%%s" %
            self.ucsc_db, serverInfo=self.ucsc_server)
        self.ens_transcripts_of_exons_map = sqlgraph.GraphView(
            self.exon_db, self.trans_db, """\
select trans.stable_id from %s.exon_stable_id exon, \
%s.transcript_stable_id trans, %s.exon_transcript et where \
exon.exon_id=et.exon_id and trans.transcript_id=et.transcript_id and \
exon.stable_id=%%s""" % (self.ens_db, self.ens_db, self.ens_db),
            serverInfo=self.ens_server)
        self.ens_transcripts_of_exons_map2 = sqlgraph.GraphView(
            self.ens_exon_stable_id, self.trans_db, """\
select trans.stable_id from %s.exon_stable_id exon, \
%s.transcript_stable_id trans, %s.exon_transcript et where \
exon.exon_id=et.exon_id and trans.transcript_id=et.transcript_id and \
exon.stable_id=%%s""" % (self.ens_db, self.ens_db, self.ens_db),
            serverInfo=self.ens_server)
        self.ens_exons_in_transcripts_map = sqlgraph.GraphView(
            self.trans_db, self.exon_db, """\
select exon.stable_id from %s.exon_stable_id exon, %s.transcript_stable_id \
trans, %s.exon_transcript et where exon.exon_id=et.exon_id and \
trans.transcript_id=et.transcript_id and trans.stable_id=%%s order by \
et.rank""" % (self.ens_db, self.ens_db, self.ens_db),
            serverInfo=self.ens_server)
        self.ens_exons_in_transcripts_map2 = sqlgraph.GraphView(
            self.trans_db, self.ens_exon_stable_id, """\
select exon.stable_id from %s.exon_stable_id exon, %s.transcript_stable_id \
trans, %s.exon_transcript et where exon.exon_id=et.exon_id and \
trans.transcript_id=et.transcript_id and trans.stable_id=%%s order by \
et.rank""" % (self.ens_db, self.ens_db, self.ens_db),
            serverInfo=self.ens_server)
        self.trans_db.exons_map = self.ens_exons_in_transcripts_map2

    def get_ensembl_db_name(self, ens_prefix, trackVersion):
        '''Used by __init__(), obtains Ensembl database name matching
        the specified UCSC genome version'''
        ucsc_versions = sqlgraph.SQLTableMultiNoCache(trackVersion,
                                               serverInfo=self.ucsc_server)
        ucsc_versions._distinct_key = 'db'
        cursor = self.ens_server.cursor()
        for t in ucsc_versions[self.ucsc_db]: # search rows until success
            if ens_prefix is None:
                # Note: this assumes 'source' in hgFixed.trackVersion contains
                # the URI of the Ensembl data set and that the last path component
                # of that URI is the species name of that data set.
                try:
                    ens_prefix1 = t.source.split('/')[-2]
                except IndexError:
                    continue
            else:
                ens_prefix1 = ens_prefix
            cursor.execute("show databases like '%s_core_%s_%%'" 
                           % (ens_prefix1, t.version))
            try:
                return cursor.fetchall()[0][0]
            except IndexError:
                pass
        raise KeyError(
                "Genome %s doesn't exist or has got no Ensembl data at UCSC" %
                self.ucsc_db)

    def get_gene_transcript_ids(self, gene_id):
        '''Obtain a list of stable IDs of transcripts associated
        with the specified gene.'''
        matching_edges = self.transcripts_in_genes_map[
            self.ucsc_ensGtp_gene[gene_id]]
        ids = []
        for transcript in matching_edges.keys():
            ids.append(transcript.name)
        return ids

    def get_annot_db(self, table, primaryKey='name',
                     sliceAttrDict=dict(id='chrom', start='chromStart',
                                        stop='chromEnd')):
        '''generic method to obtain an AnnotationDB for any
        annotation table in UCSC, e.g. snp130.  If your target table
        has non-standard name, start, end columns, specify them in
        the primaryKey and sliceAttrDict args.
        Saves table as named attribute on this package object.'''
        try: # return existing db if already cached here
            return getattr(self, table)
        except AttributeError:
            pass
        sliceDB = sqlgraph.SQLTable(self.ucsc_db + '.' + table,
                                    primaryKey=primaryKey,
                                    serverInfo=self.ucsc_server,
                                    itemClass=UCSCSeqIntervalRow)
        annoDB = annotation.AnnotationDB(sliceDB, self.genome_seq,
                                         checkFirstID=False,
                                         sliceAttrDict=sliceAttrDict)
        setattr(self, table, annoDB) # cache this db on named attribute
        return annoDB


class EnsemblTranscriptAnnotationSeqDescr(object):

    def __init__(self, attr):
        self.attr = attr

    def __get__(self, obj, objtype):
        '''Concatenate exon sequences of a transcript to obtain
        its sequence.'''
        exon_count = obj.exonCount
        exon_starts = obj.exonStarts.split(',')[:exon_count]
        exon_ends = obj.exonEnds.split(',')[:exon_count]
        trans_seq = ''
        for i in range(0, exon_count):
            trans_seq += str(sequence.absoluteSlice(obj._anno_seq,
                                                    int(exon_starts[i]),
                                                    int(exon_ends[i])))
        seq = sequence.Sequence(trans_seq, obj.name)
        setattr(obj, self.attr, seq) # cache on object
        return seq


class EnsemblTranscriptAnnotationSeq(annotation.AnnotationSeq):
    '''An AnnotationSeq class for transcript annotations, implementing
    custom 'mrna_sequence' property.'''
    mrna_sequence = EnsemblTranscriptAnnotationSeqDescr('mrna_sequence')

    def get_exon_slices(self):
        '''Parse the provided transcript, extract exon data from it
        and return it as a dictionary of slices.'''
        chromosome = self.chrom
        exon_count = self.exonCount
        exon_starts = self.exonStarts.split(',')[:exon_count]
        exon_ends = self.exonEnds.split(',')[:exon_count]
        exons = {}
        exon_ids = self.get_ensembl_exon_ids()
        for i in range(exon_count):
            exons[exon_ids[i]] = (chromosome, exon_starts[i], exon_ends[i],
                                  self.orientation)
        return exons

    def get_ensembl_exon_ids(self):
        '''Obtain a list of stable IDs of exons associated with the
        specified transcript, ordered by rank.'''
        matching_edges = self.db.exons_map[self]
        return [exon.stable_id for exon in matching_edges.keys()]


class EnsemblProteinSeqDescr(object):

    def __init__(self, attr):
        self.attr = attr

    def __get__(self, obj, objtype):
        transcript = obj.db.gRes.protein_transcript_id_map[obj]
        pep = obj.db.gRes.ucsc_ensPep[transcript.name]
        seq = sequence.Sequence(str(pep), obj.id)
        setattr(obj, self.attr, seq) # cache on object
        return seq


class EnsemblProteinRow(sqlgraph.TupleO):
    sequence = EnsemblProteinSeqDescr('sequence')

    def __repr__(self):
        return str(self.id)


class EnsemblExonOnDemandSliceDB(object, UserDict.DictMixin):
    '''Obtains exon info on demand by looking up associated transcript '''

    def __init__(self, gRes):
        self.data = {}
        self.gRes = gRes

    def __getitem__(self, k):
        try:
            return self.data[k]
        except KeyError:
            # Not cached yet, extract the exon from transcript data.
            transcripts = self.gRes.ens_transcripts_of_exons_map2[
                self.gRes.ens_exon_stable_id[k]].keys()
            self.data.update(transcripts[0].get_exon_slices())
            # Cache whole transcript interval to speed sequence access
            self.gRes.genome_seq.cacheHint({transcripts[0].id:
                                           (transcripts[0].txStart,
                                            transcripts[0].txEnd)},
                                           transcripts[0])
            return self.data[k]

    __setitem__ = __delitem__ = read_only_error # Throws an exception

    def keys(self): # mirror iterator methods from exon stable ID table
        return self.gRes.ens_exon_stable_id.keys()

    def __iter__(self):
        return iter(self.gRes.ens_exon_stable_id)

    def __len__(self):
        return len(self.gRes.ens_exon_stable_id)

########NEW FILE########
__FILENAME__ = blast
import glob
import os
import tempfile
import classutil
import logger
from sequtil import *
from parse_blast import BlastHitParser
from seqdb import write_fasta, read_fasta
from nlmsa_utils import CoordsGroupStart, CoordsGroupEnd, CoordsToIntervals,\
     EmptySlice
from annotation import AnnotationDB, TranslationAnnot, TranslationAnnotSlice
import cnestedlist
import translationDB
import UserDict

# NCBI HAS THE NASTY HABIT OF TREATING THE IDENTIFIER AS A BLOB INTO
# WHICH THEY STUFF FIELD AFTER FIELD... E.G. gi|1234567|foobarU|NT_1234567|...
# THIS JUST YANKS OUT THE SECOND ARGUMENT SEPARATED BY |
NCBI_ID_PARSER=lambda id: id.split('|')[1]


def blast_program(query_type, db_type):
    progs = {DNA_SEQTYPE: {DNA_SEQTYPE: 'blastn', PROTEIN_SEQTYPE: 'blastx'},
            PROTEIN_SEQTYPE: {DNA_SEQTYPE: 'tblastn',
                              PROTEIN_SEQTYPE: 'blastp'}}
    if query_type == RNA_SEQTYPE:
        query_type = DNA_SEQTYPE
    if db_type == RNA_SEQTYPE:
        db_type = DNA_SEQTYPE
    return progs[query_type][db_type]


def read_blast_alignment(ofile, srcDB, destDB, al=None, pipeline=None,
                         translateSrc=False, translateDest=False):
    """Apply sequence of transforms to read input from 'ofile'.

    srcDB: database for finding query sequences from the blast input;

    destDB: database for finding subject sequences from the blast input;

    al, if not None, must be a writeable alignment object in which to
    store the alignment intervals;

    translateSrc=True forces creation of a TranslationDB representing
    the possible 6-frames of srcDB (for blastx, tblastx);

    translateDest=True forces creation of a TranslationDB representing
    the possible 6-frames of destDB (for tblastn, tblastx).

    If pipeline is not None, it must be a list of filter functions each
    taking a single argument and returning an iterator or iterable result
    object.
    """
    p = BlastHitParser()
    d = dict(id='src_id', start='src_start', stop='src_end', ori='src_ori',
             idDest='dest_id', startDest='dest_start',
             stopDest='dest_end', oriDest='dest_ori')
    if translateSrc:
        srcDB = translationDB.get_translation_db(srcDB)
    if translateDest:
        destDB = translationDB.get_translation_db(destDB)
    cti = CoordsToIntervals(srcDB, destDB, d)
    alignedIvals = cti(p.parse_file(ofile))
    if pipeline is None:
        result = save_interval_alignment(alignedIvals, al)
    else: # apply all the filters in our pipeline one by one
        result = alignedIvals
        for f in pipeline:
            result = f(result)
    return result


def save_interval_alignment(alignedIvals, al=None):
    """Save alignedIvals to al, or a new in-memory NLMSA"""
    needToBuild = False
    if al is None:
        al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True,
                               bidirectional=False)
        needToBuild = True
    al.add_aligned_intervals(alignedIvals)
    if needToBuild:
        al.build()
    return al


def start_blast(cmd, seq, seqString=None, seqDict=None, **kwargs):
    """Run blast and return results."""
    p = classutil.FilePopen(cmd, stdin=classutil.PIPE, stdout=classutil.PIPE,
                            **kwargs)
    if seqString is None:
        seqString = seq
    if seqDict is not None: # write all seqs to nonblocking ifile
        for seqID, seq in seqDict.iteritems():
            write_fasta(p.stdin, seq)
        seqID = None
    else: # just write one query sequence
        seqID = write_fasta(p.stdin, seqString)
    if p.wait(): # blast returned error code
        raise OSError('command %s failed' % ' '.join(cmd))
    return seqID, p


def process_blast(cmd, seq, blastDB, al=None, seqString=None, queryDB=None,
                  popenArgs={}, **kwargs):
    """Run blast and return an alignment."""
    seqID, p = start_blast(cmd, seq, seqString, seqDict=queryDB, **popenArgs)
    try:
        if not queryDB: # need a query db for translation / parsing results
            try:
                queryDB = seq.db # use this sequence's database
            except AttributeError:
                queryDB = {seqID: seq} # construct a trivial "database"

        al = read_blast_alignment(p.stdout, queryDB, blastDB, al, **kwargs)
    finally:
        p.close() # close our PIPE files
    return al


def repeat_mask(seq, progname='RepeatMasker', opts=()):
    'Run RepeatMasker on a sequence, return lowercase-masked string'
    ## fd, temppath = tempfile.mkstemp()
    ## ofile = os.fdopen(fd, 'w') # text file
    p = classutil.FilePopen([progname] + list(opts), stdin=classutil.PIPE,
                            stdinFlag=None)
    write_fasta(p.stdin, seq, reformatter=lambda x: x.upper()) # save uppercase
    try:
        if p.wait():
            raise OSError('command %s failed' % ' '.join(p.args[0]))
        ifile = file(p._stdin_path + '.masked', 'rU') # text file
        try:
            for id, title, seq_masked in read_fasta(ifile):
                break # JUST READ ONE SEQUENCE
        finally:
            ifile.close()
    finally: # clean up our temp files no matter what happened
        p.close() # close temp stdin file
        for fpath in glob.glob(p._stdin_path + '.*'):
            try:
                os.remove(fpath)
            except OSError:
                pass
    return seq_masked # ONLY THE REPEATS ARE IN LOWERCASE NOW


def warn_if_whitespace(filepath):
    l = filepath.split() # check filepath for whitespace
    if len(l) > 1 or len(l[0]) < len(filepath): # contains whitespace
        logger.warn("""
Your sequence filepath contains whitespace characters:
%s
The NCBI formatdb (and blastall) programs cannot handle file paths
containing whitespace! This is a known NCBI formatdb / blastall bug.
Please use a path containing no whitespace characters!""" % filepath)
        return True # signal caller that a warning was issued


class BlastMapping(object):
    'Graph interface for mapping a sequence to homologs in a seq db via BLAST'

    def __init__(self, seqDB, filepath=None, blastReady=False,
                 blastIndexPath=None, blastIndexDirs=None, verbose=True,
                 showFormatdbMessages=True, **kwargs):
        '''seqDB: sequence database object to search for homologs
        filepath: location of FASTA format file for the sequence database
        blastReady: if True, ensure that BLAST index file ready to use
        blastIndexPath: location of the BLAST index file
        blastIndexDirs: list of directories for trying to build index in
        '''
        self.seqDB = seqDB
        self.idIndex = BlastIDIndex(seqDB)
        self.verbose = verbose
        self.showFormatdbMessages = showFormatdbMessages
        if filepath is not None:
            self.filepath = filepath
        else:
            self.filepath = seqDB.filepath
        if blastIndexPath is not None:
            self.blastIndexPath = blastIndexPath
        if blastIndexDirs is not None:
            self.blastIndexDirs = blastIndexDirs
        self.checkdb() # CHECK WHETHER BLAST INDEX FILE IS PRESENT...
        if not self.blastReady and blastReady: # FORCE CONSTRUCTION OF BLAST DB
            self.formatdb()

    def __repr__(self):
        return "<BlastMapping '%s'>" % (self.filepath)

    def __getitem__(self, k):
        'return NLMSASlice representing BLAST results'
        al = self.__call__(k) # run BLAST & get NLMSA storing results
        return al[k] # return NLMSASlice representing these results

    def test_db_location(self, testpath):
        '''check whether BLAST index files ready for use; return status.'''
        if not os.access(testpath+'.nsd', os.R_OK) \
               and not os.access(testpath+'.psd', os.R_OK) \
               and not os.access(testpath+'.00.nsd', os.R_OK) \
               and not os.access(testpath+'.00.psd', os.R_OK):
            return False
        else: # FOUND INDEX FILES IN THIS LOCATION
            if testpath != self.filepath:
                self.blastIndexPath = testpath
            return True

    def checkdb(self):
        'look for blast index files in blastIndexPath, \
        standard list of locations'
        for testpath in self.blast_index_paths():
            self.blastReady = self.test_db_location(testpath)
            if self.blastReady:
                break
        return self.blastReady

    def run_formatdb(self, testpath):
        'ATTEMPT TO BUILD BLAST DATABASE INDEXES at testpath'
        dirname = classutil.file_dirpath(testpath)
        if not os.access(dirname, os.W_OK): # check if directory is writable
            raise IOError('run_formatdb: directory %s is not writable!'
                          % dirname)
        cmd = ['formatdb', '-i', self.filepath, '-n', testpath, '-o', 'T']
        if self.seqDB._seqtype != PROTEIN_SEQTYPE:
            cmd += ['-p', 'F'] # special flag required for nucleotide seqs
        logger.info('Building index: ' + ' '.join(cmd))
        if self.showFormatdbMessages:
            kwargs = {}
        else: # suppress formatdb messages by redirecting them
            kwargs = dict(stdout=classutil.PIPE, stderr=classutil.PIPE)
        if classutil.call_subprocess(cmd, **kwargs):
            # bad exit code, so command failed
            warn_if_whitespace(self.filepath) \
                 or warn_if_whitespace(testpath) # only issue one warning
            raise OSError('command %s failed' % ' '.join(cmd))
        self.blastReady=True
        if testpath!=self.filepath:
            self.blastIndexPath = testpath

    def get_blast_index_path(self):
        'get path to base name for BLAST index files'
        try:
            return self.blastIndexPath
        except AttributeError:
            return self.filepath
    # DEFAULT: BUILD INDEX FILES IN self.filepath . HOME OR APPROPRIATE
    # USER-/SYSTEM-SPECIFIC TEMPORARY DIRECTORY
    blastIndexDirs = ['FILEPATH', os.getcwd, os.path.expanduser,
                      tempfile.gettempdir()]

    def blast_index_paths(self):
        'iterate over possible blast index directories'
        try: # 1ST TRY ACTUAL SAVED LOCATION IF ANY
            yield self.blastIndexPath
        except AttributeError:
            pass
        for m in self.blastIndexDirs: # NOW TRY STANDARD LOCATIONS
            if m=='FILEPATH':
                yield self.filepath
                continue
            elif m == os.path.expanduser:
                s = m('~') # GET HOME DIRECTORY
            elif callable(m):
                s = m()
            else: # TREAT AS STRING
                s = str(m)
            yield os.path.join(s, os.path.basename(self.filepath))

    def formatdb(self, filepath=None):
        'try to build BLAST index files in an appropriate location'
        if filepath is not None: # JUST USE THE SPECIFIED PATH
            return self.run_formatdb(filepath)
        notFirst = False
        for testpath in self.blast_index_paths():
            if notFirst:
                logger.info('Trying next entry in self.blastIndexDirs...')
            notFirst = True
            try: # BUILD IN TARGET DIRECTORY
                return self.run_formatdb(testpath)
            except (IOError, OSError): # BUILD FAILED
                pass
        raise IOError("cannot build BLAST database for %s" % (self.filepath, ))

    def raw_fasta_stream(self, ifile=None, idFilter=None):
        '''Return a stream of fasta-formatted sequences.

        Optionally, apply an ID filter function if supplied.
        '''
        if ifile is not None: # JUST USE THE STREAM WE ALREADY HAVE OPEN
            return ifile, idFilter
        try: # DEFAULT: JUST READ THE FASTA FILE, IF IT EXISTS
            return file(self.filepath, 'rU'), idFilter
        except IOError: # TRY READING FROM FORMATTED BLAST DATABASE
            cmd='fastacmd -D -d "%s"' % self.get_blast_index_path()
            return os.popen(cmd), NCBI_ID_PARSER #BLAST ADDS lcl| TO id


    _blast_prog_dict = dict(blastx='#BlastxMapping')

    def blast_program(self, seq, blastprog=None):
        'figure out appropriate blast program & remap via _blast_prog_dict'
        if blastprog is None:
            blastprog = blast_program(seq.seqtype(), self.seqDB._seqtype)
        oldprog = blastprog
        try: # apply program transformation if provided
            blastprog = self._blast_prog_dict[blastprog]
            if blastprog.startswith('#'): # not permitted by this class!
                raise ValueError('Use %s for %s' % (blastprog[1:], oldprog))
        except KeyError:
            pass # no program transformation to apply, so nothing to do...
        return blastprog

    def blast_command(self, blastpath, blastprog, expmax, maxseq, opts):
        'generate command string for running blast with desired options'
        filepath = self.get_blast_index_path()
        warn_if_whitespace(filepath)
        cmd = [blastpath, '-d', filepath, '-p', blastprog,
                '-e', '%e' % float(expmax)] + list(opts)
        if maxseq is not None: # ONLY TAKE TOP maxseq HITS
            cmd += ['-b', '%d' % maxseq, '-v', '%d' % maxseq]
        return cmd

    def get_seq_from_queryDB(self, queryDB):
        'get one sequence obj from queryDB'
        seqID = iter(queryDB).next() # get 1st seq ID
        return queryDB[seqID]

    def translation_kwargs(self, blastprog):
        'return kwargs for read_blast_alignment() based on blastprog'
        d = dict(tblastn=dict(translateDest=True),
                 blastx=dict(translateSrc=True),
                 tblastx=dict(translateSrc=True, translateDest=True))
        try:
            return d[blastprog]
        except KeyError:
            return {}

    def __call__(self, seq=None, al=None, blastpath='blastall',
                 blastprog=None, expmax=0.001, maxseq=None, verbose=None,
                 opts=(), queryDB=None, **kwargs):
        "Run blast search for seq in database, return alignment object"
        if seq is None and queryDB is None:
            raise ValueError("we need a sequence or db to use as query!")
        if seq and queryDB:
            raise ValueError("both a sequence AND a db provided for query")
        if queryDB is not None:
            seq = self.get_seq_from_queryDB(queryDB)
        if not self.blastReady: # HAVE TO BUILD THE formatdb FILES...
            self.formatdb()
        blastprog = self.blast_program(seq, blastprog)
        cmd = self.blast_command(blastpath, blastprog, expmax, maxseq, opts)
        return process_blast(cmd, seq, self.idIndex, al, queryDB=queryDB,
                             ** self.translation_kwargs(blastprog))


class BlastxMapping(BlastMapping):
    """Because blastx changes the query to multiple sequences
    (representing its six possible frames), getitem can no longer
    return a single slice object, but instead an iterator for one
    or more slice objects representing the frames that had
    homology hits."""

    def __repr__(self):
        return "<BlastxMapping '%s'>" % (self.filepath)
    _blast_prog_dict = dict(blastn='tblastx', blastp='#BlastMapping',
                            tblastn='#BlastMapping')

    def __getitem__(self, query):
        """generate slices for all translations of the query """
        # generate NLMSA for this single sequence
        al = self(query)
        # get the translation database for the sequence
        tdb = translationDB.get_translation_db(query.db)

        # run through all of the frames & find alignments.
        slices = []
        for trans_seq in tdb[query.id].iter_frames():
            try:
                slice = al[trans_seq]
            except KeyError:
                continue

            if not isinstance(slice, EmptySlice):
                slices.append(slice)

        return slices


class MegablastMapping(BlastMapping):

    def __repr__(self):
        return "<MegablastMapping '%s'>" % (self.filepath)

    def __call__(self, seq, al=None, blastpath='megablast', expmax=1e-20,
                 maxseq=None, minIdentity=None,
                 maskOpts=['-U', 'T', '-F', 'm'],
                 rmPath='RepeatMasker', rmOpts=['-xsmall'],
                 verbose=None, opts=(), **kwargs):
        "Run megablast search with optional repeat masking."
        if not self.blastReady: # HAVE TO BUILD THE formatdb FILES...
            self.formatdb()

        # mask repeats to lowercase
        masked_seq = repeat_mask(seq, rmPath, rmOpts)
        filepath = self.get_blast_index_path()
        warn_if_whitespace(filepath)
        cmd = [blastpath] + maskOpts \
              + ['-d', filepath,
                 '-D', '2', '-e', '%e' % float(expmax)] + list(opts)
        if maxseq is not None: # ONLY TAKE TOP maxseq HITS
            cmd += ['-b', '%d' % maxseq, '-v', '%d' % maxseq]
        if minIdentity is not None:
            cmd += ['-p', '%f' % float(minIdentity)]
        return process_blast(cmd, seq, self.idIndex, al, seqString=masked_seq,
                             popenArgs=dict(stdinFlag='-i'))


class BlastIDIndex(object):
    """This class acts as a wrapper around a regular seqDB, and handles
    the mangled IDs returned by BLAST to translate them to the correct ID.
    Since NCBI treats FASTA ID as a blob into which they like to stuff
    many fields... and then NCBI BLAST mangles those IDs when it reports
    hits, so they no longer match the true ID... we are forced into
    contortions to rescue the true ID from mangled IDs.

    Our workaround strategy: since NCBI packs the FASTA ID with multiple
    IDs (GI, GB, RefSeq ID etc.), we can use any of these identifiers
    that are found in a mangled ID, by storing a mapping of these
    sub-identifiers to the true FASTA ID."""

    def __init__(self, seqDB):
        self.seqDB = seqDB
        self.seqInfoDict = BlastIDInfoDict(self)
    # FOR UNPACKING NCBI IDENTIFIERS AS WORKAROUND FOR BLAST ID CRAZINESS
    id_delimiter='|'

    def unpack_id(self, id):
        """Return |-packed NCBI identifiers as unpacked list.

        NCBI packs identifier like gi|123456|gb|A12345|other|nonsense.
        Return as list."""
        return id.split(self.id_delimiter)

    def index_unpacked_ids(self, unpack_f=None):
        """Build an index of sub-IDs (unpacked from NCBI nasty habit
        of using the FASTA ID as a blob); you can customize the unpacking
        by overriding the unpack_id function or changing the id_delimiter.
        The index maps each sub-ID to the real ID, so that when BLAST
        hands back a mangled, fragmentary ID, we can unpack that mangled ID
        and look up the true ID in this index.  Any sub-ID that is found
        to map to more than one true ID will be mapped to None (so that
        random NCBI garbage like gnl or NCBI_MITO wont be treated as
        sub-IDs).
        """
        if unpack_f is None:
            unpack_f=self.unpack_id
        t={}
        for id in self.seqDB:
            for s in unpack_f(id):
                if s == id:
                    continue # DON'T STORE TRIVIAL MAPPINGS!!
                s=s.upper() # NCBI FORCES ID TO UPPERCASE?!?!
                try:
                    if t[s]!=id and t[s] is not None:
                        t[s]=None # s NOT UNIQUE, CAN'T BE AN IDENTIFIER!!
                except KeyError:
                    t[s]=id # s UNIQUE, TRY USING s AS AN IDENTIFIER
        for id in t.itervalues():
            if id is not None: # OK THERE ARE REAL MAPPINGS STORED, SO USE THIS
                self._unpacked_dict=t # SAVE THE MAPPING TO REAL IDENTIFIERS
                return
        # NO NON-TRIVIAL MAPPINGS, SO JUST SAVE EMPTY MAPPING
        self._unpacked_dict={}

    def get_real_id(self, bogusID, unpack_f=None):
        "try to translate an id that NCBI has mangled to the real sequence id"
        if unpack_f is None:
            unpack_f = self.unpack_id
        if not hasattr(self, '_unpacked_dict'):
            self.index_unpacked_ids(unpack_f)
        for s in unpack_f(bogusID):
            s = s.upper() # NCBI FORCES ID TO UPPERCASE?!?!
            try:
                id = self._unpacked_dict[s]
                if id is not None:
                    return id # OK, FOUND A MAPPING TO REAL ID
            except KeyError:
                pass # KEEP TRYING...
        # FOUND NO MAPPING, SO RAISE EXCEPTION
        raise KeyError("no key '%s' in database %s" % (bogusID,
                                                        repr(self.seqDB)))

    def __getitem__(self, seqID):
        "If seqID is mangled by BLAST, use our index to get correct ID"
        try: # default: treat as a correct ID
            return self.seqDB[seqID]
        except KeyError: # translate to the correct ID
            return self.seqDB[self.get_real_id(seqID)]

    def __contains__(self, seqID):
        try:
            self.seqInfoDict[seqID]
            return True
        except KeyError:
            return False


class BlastIDInfoDict(object, UserDict.DictMixin):
    """provide seqInfoDict interface for BlastIDIndex """

    def __init__(self, db):
        self.blastDB = db

    def __getitem__(self, seqID):
        try:
            return self.blastDB.seqDB.seqInfoDict[seqID]
        except KeyError:
            seqID = self.blastDB.get_real_id(seqID)
            return self.blastDB.seqDB.seqInfoDict[seqID]

    def __len__(self):
        return len(self.blastDB.seqDB.seqInfoDict)

    def __iter__(self):
        return iter(self.blastDB.seqDB.seqInfoDict)

    def keys(self):
        return self.blastDB.seqDB.seqInfoDict.keys()

########NEW FILE########
__FILENAME__ = classutil
import os
import sys
import tempfile
from weakref import WeakValueDictionary
import dbfile
import logger


class FilePopenBase(object):
    '''Base class for subprocess.Popen-like class interface that
can be supported on Python 2.3 (without subprocess).  The main goal
is to avoid the pitfalls of Popen.communicate(), which cannot handle
more than a small amount of data, and to avoid the possibility of deadlocks
and the issue of threading, by using temporary files'''

    def __init__(self, args, bufsize=0, executable=None,
                 stdin=None, stdout=None, stderr=None, *largs, **kwargs):
        '''Mimics the interface of subprocess.Popen() with two additions:
- stdinFlag, if passed, gives a flag to add the stdin filename directly
to the command line (rather than passing it by redirecting stdin).
example: stdinFlag="-i" will add the following to the commandline:
-i /path/to/the/file
If set to None, the stdin filename is still appended to the commandline,
but without a preceding flag argument.

-stdoutFlag: exactly the same thing, except for the stdout filename.
'''
        self.stdin, self._close_stdin = self._get_pipe_file(stdin, 'stdin')
        self.stdout, self._close_stdout = self._get_pipe_file(stdout, 'stdout')
        self.stderr, self._close_stderr = self._get_pipe_file(stderr, 'stderr')
        kwargs = kwargs.copy() # get a copy we can change
        try: # add as a file argument
            stdinFlag = kwargs['stdinFlag']
            if stdinFlag:
                args.append(stdinFlag)
            args.append(self._stdin_path)
            del kwargs['stdinFlag']
            stdin = None
        except KeyError: # just make it read this stream
            stdin = self.stdin
        try: # add as a file argument
            stdoutFlag = kwargs['stdoutFlag']
            if stdoutFlag:
                args.append(stdoutFlag)
            args.append(self._stdout_path)
            del kwargs['stdoutFlag']
            stdout = None
        except KeyError: # make it write to this stream
            stdout = self.stdout
        self.args = (args, bufsize, executable, stdin, stdout,
                     self.stderr) + largs
        self.kwargs = kwargs

    def _get_pipe_file(self, ifile, attr):
        'create a temp filename instead of a PIPE; save the filename'
        if ifile == PIPE: # use temp file instead!
            fd, path = tempfile.mkstemp()
            setattr(self, '_' + attr + '_path', path)
            return os.fdopen(fd, 'w+b'), True
        elif ifile is not None:
            setattr(self, '_' + attr + '_path', ifile.name)
        return ifile, False

    def _close_file(self, attr):
        'close and delete this temp file if still open'
        if getattr(self, '_close_' + attr):
            getattr(self, attr).close()
            setattr(self, '_close_' + attr, False)
            os.remove(getattr(self, '_' + attr + '_path'))

    def _rewind_for_reading(self, ifile):
        if ifile is not None:
            ifile.flush()
            ifile.seek(0)

    def close(self):
        """Close any open temp (PIPE) files. """
        self._close_file('stdin')
        self._close_file('stdout')
        self._close_file('stderr')

    def __del__(self):
        self.close()


def call_subprocess(*popenargs, **kwargs):
    'portable interface to subprocess.call(), even if subprocess not available'
    p = FilePopen(*popenargs, **kwargs)
    return p.wait()

try:
    import subprocess
    PIPE = subprocess.PIPE

    class FilePopen(FilePopenBase):
        'this subclass uses the subprocess module Popen() functionality'

        def wait(self):
            self._rewind_for_reading(self.stdin)
            p = subprocess.Popen(*self.args, **self.kwargs)
            p.wait()
            self._close_file('stdin')
            self._rewind_for_reading(self.stdout)
            self._rewind_for_reading(self.stderr)
            return p.returncode

except ImportError:
    CSH_REDIRECT = False # SH style redirection is default
    import platform
    if platform.system() == 'Windows':

        def mkarg(arg):
            """Very basic quoting of arguments for Windows """
            return '"' + arg + '"'
    else: # UNIX
        from commands import mkarg
        try:
            if os.environ['SHELL'].endswith('csh'):
                CSH_REDIRECT = True
        except KeyError:
            pass

    badExecutableCode = None

    class FilePopen(FilePopenBase):
        'this subclass fakes subprocess.Popen.wait() using os.system()'

        def wait(self):
            self._rewind_for_reading(self.stdin)
            args = map(mkarg, self.args[0])
            if self.args[3]: # redirect stdin
                args += ['<', mkarg(self._stdin_path)]
            if self.args[4]: # redirect stdout
                args += ['>', mkarg(self._stdout_path)]
            cmd = ' '.join(args)
            if self.args[5]: # redirect stderr
                if CSH_REDIRECT:
                    cmd = '(%s) >& %s' % (cmd, mkarg(self._stderr_path))
                else:
                    cmd = cmd + ' 2> ' + mkarg(self._stderr_path)
            returncode = os.system(cmd)
            self._close_file('stdin')
            self._rewind_for_reading(self.stdout)
            self._rewind_for_reading(self.stderr)
            if badExecutableCode is not None and \
               badExecutableCode == returncode:
                raise OSError('no such command: %s' % str(self.args[0]))
            return returncode
    PIPE = id(FilePopen) # an arbitrary code for identifying this code

    # find out exit code for a bad executable name, silently
    badExecutableCode = call_subprocess(('aZfDqW9', ),
                                        stdout=PIPE, stderr=PIPE)


def ClassicUnpickler(cls, state):
    'standard python unpickling behavior'
    self = cls.__new__(cls)
    try:
        setstate = self.__setstate__
    except AttributeError: # JUST SAVE TO __dict__ AS USUAL
        self.__dict__.update(state)
    else:
        setstate(state)
    return self

ClassicUnpickler.__safe_for_unpickling__ = 1


def filename_unpickler(cls, path, kwargs):
    'raise IOError if path not readable'
    if not os.path.exists(path):
        try:# CONVERT TO ABSOLUTE PATH BASED ON SAVED DIRECTORY PATH
            path = os.path.normpath(os.path.join(kwargs['curdir'], path))
            if not os.path.exists(path):
                raise IOError('unable to open file %s' % path)
        except KeyError:
            raise IOError('unable to open file %s' % path)
    if cls is SourceFileName:
        return SourceFileName(path)
    raise ValueError('Attempt to unpickle untrusted class ' + cls.__name__)

filename_unpickler.__safe_for_unpickling__ = 1


class SourceFileName(str):
    '''store a filepath string, raise IOError on unpickling
if filepath not readable, and complain if the user tries
to pickle a relative path'''

    def __reduce__(self):
        if not os.path.isabs(str(self)):
            print >>sys.stderr, '''
WARNING: You are trying to pickle an object that has a local
file dependency stored only as a relative file path:
%s
This is not a good idea, because anyone working in
a different directory would be unable to unpickle this object,
since it would be unable to find the file using the relative path.
To avoid this problem, SourceFileName is saving the current
working directory path so that it can translate the relative
path to an absolute path.  In the future, please use absolute
paths when constructing objects that you intend to save to worldbase
or pickle!''' % str(self)
        return (filename_unpickler, (self.__class__, str(self),
                                    dict(curdir=os.getcwd())))


def file_dirpath(filename):
    'return path to directory containing filename'
    dirname = os.path.dirname(filename)
    if dirname == '':
        return os.curdir
    else:
        return dirname


def get_valid_path(*pathTuples):
    '''for each tuple in args, build path using os.path.join(),
    and return the first path that actually exists, or else None.'''
    for t in pathTuples:
        mypath = os.path.join(*t)
        if os.path.exists(mypath):
            return mypath


def search_dirs_for_file(filepath, pathlist=()):
    'return successful path based on trying pathlist locations'
    if os.path.exists(filepath):
        return filepath
    b = os.path.basename(filepath)
    for s in pathlist: # NOW TRY EACH DIRECTORY IN pathlist
        mypath = os.path.join(s, b)
        if os.path.exists(mypath):
            return mypath
    raise IOError('unable to open %s from any location in %s'
                  % (filepath, pathlist))


def report_exception():
    'print string message from exception to stderr'
    import traceback
    info = sys.exc_info()[:2]
    l = traceback.format_exception_only(info[0], info[1])
    print >>sys.stderr, 'Warning: caught %s\nContinuing...' % l[0]


def standard_invert(self):
    'keep a reference to an inverse mapping, using self._inverseClass'
    try:
        return self._inverse
    except AttributeError:
        self._inverse = self._inverseClass(self)
        return self._inverse


def lazy_create_invert(klass):
    """Create a function to replace __invert__ with a call to a cached object.

    lazy_create_invert defines a method that looks up self._inverseObj
    and, it it doesn't exist, creates it from 'klass' and then saves it.
    The resulting object is then returned as the inverse.  This allows
    for one-time lazy creation of a single object per parent class.
    """

    def invert_fn(self, klass=klass):
        try:
            return self._inverse
        except AttributeError:
            # does not exist yet; create & store.
            inverseObj = klass(self)
            self._inverse = inverseObj
            return inverseObj

    return invert_fn


def standard_getstate(self):
    'get dict of attributes to save, using self._pickleAttrs dictionary'
    d = {}
    for attr, arg in self._pickleAttrs.items():
        try:
            if isinstance(arg, str):
                d[arg] = getattr(self, attr)
            else:
                d[attr] = getattr(self, attr)
        except AttributeError:
            pass
    try:
        # DON'T SAVE itemClass IF SIMPLY A SHADOW of default itemClass
        # from __class__
        if not hasattr(self.__class__, 'itemClass') or \
           (self.itemClass is not self.__class__.itemClass and
            (not hasattr(self.itemClass, '_shadowParent') or
             self.itemClass._shadowParent is not self.__class__.itemClass)):
            try:
                d['itemClass'] = self.itemClass._shadowParent
            except AttributeError:
                d['itemClass'] = self.itemClass
        if not hasattr(self.__class__, 'itemSliceClass') or \
           (self.itemSliceClass is not self.__class__.itemSliceClass and
            (not hasattr(self.itemSliceClass, '_shadowParent') or
             self.itemSliceClass._shadowParent is not
             self.__class__.itemSliceClass)):
            try:
                d['itemSliceClass'] = self.itemSliceClass._shadowParent
            except AttributeError:
                d['itemSliceClass'] = self.itemSliceClass
    except AttributeError:
        pass
    try: # SAVE CUSTOM UNPACKING METHOD
        d['unpack_edge'] = self.__dict__['unpack_edge']
    except KeyError:
        pass
    return d


def standard_setstate(self, state):
    'apply dict of saved state by passing as kwargs to constructor'
    if isinstance(state, list):  # GET RID OF THIS BACKWARDS-COMPATIBILITY CODE
        self.__init__(*state)
        print >>sys.stderr, 'WARNING: obsolete list pickle %s. Update \
                by resaving!' % repr(self)
    else:
        state['unpicklingMode'] = True # SIGNAL THAT WE ARE UNPICKLING
        self.__init__(**state)


def apply_itemclass(self, state):
    try:
        self.itemClass = state['itemClass']
        self.itemSliceClass = state['itemSliceClass']
    except KeyError:
        pass


def generate_items(items):
    'generate o.id,o for o in items'
    for o in items:
        yield o.id, o


def item_unpickler(db, *args):
    'get an item or subslice of a database'
    obj = db
    for arg in args:
        obj = obj[arg]
    return obj
item_unpickler.__safe_for_unpickling__ = 1


def item_reducer(self): ############################# SUPPORT FOR PICKLING
    'pickle an item of a database just as a reference'
    return (item_unpickler, (self.db, self.id))


def shadow_reducer(self):
    'pickle shadow class instance using its true class'
    shadowClass = self.__class__
    trueClass = shadowClass._shadowParent # super() TOTALLY FAILED ME HERE!
    self.__class__ = trueClass # FORCE IT TO PICKLE USING trueClass
    keepDB = False
    if hasattr(shadowClass, 'db') and not hasattr(self, 'db'):
        keepDB = True
        self.__dict__['db'] = shadowClass.db # retain this attribute!!
    if hasattr(trueClass, '__reduce__'): # USE trueClass.__reduce__
        result = trueClass.__reduce__(self)
    elif hasattr(trueClass, '__getstate__'): # USE trueClass.__getstate__
        result = (ClassicUnpickler, (trueClass, self.__getstate__()))
    else: # PICKLE __dict__ AS USUAL PYTHON PRACTICE
        result = (ClassicUnpickler, (trueClass, self.__dict__))
    self.__class__ = shadowClass # RESTORE SHADOW CLASS
    if keepDB: # now we can drop the temporary db attribute we added
        del self.__dict__['db']
    return result


def get_bound_subclass(obj, classattr='__class__', subname=None, factories=(),
                       attrDict=None, subclassArgs=None):
    'create a subclass specifically for obj to bind its shadow attributes'
    targetClass = getattr(obj, classattr)
    try:
        if targetClass._shadowOwner is obj:
            return targetClass # already shadowed, so nothing to do
    except AttributeError: # not a shadow class, so just shadow it
        pass
    else: # someone else's shadow class, so shadow its parent
        targetClass = targetClass._shadowParent
    if subname is None: # get a name from worldbase ID
        try:
            subname = obj._persistent_id.split('.')[-1]
        except AttributeError:
            subname = '__generic__'

    class shadowClass(targetClass):
        __reduce__ = shadow_reducer
        _shadowParent = targetClass # NEED TO KNOW ORIGINAL CLASS
        _shadowOwner = obj # need to know who owns it
        if attrDict is not None: # add attributes to the class dictionary
            locals().update(attrDict)
        for f in factories:
            f(locals())

    if classattr == 'itemClass' or classattr == 'itemSliceClass':
        shadowClass.db = obj # the class needs to know its db object
    try: # run subclass initializer if present
        subclass_init = shadowClass._init_subclass
    except AttributeError: # no subclass initializer, so nothing to do
        pass
    else: # run the subclass initializer
        if subclassArgs is None:
            subclassArgs = {}
        subclass_init(**subclassArgs)
    shadowClass.__name__ = targetClass.__name__ + '_' + subname
    setattr(obj, classattr, shadowClass) # SHADOW CLASS REPLACES ORIGINAL
    return shadowClass


def method_not_implemented(*args, **kwargs):
    raise NotImplementedError


def read_only_error(*args, **kwargs):
    raise NotImplementedError("read only dict")


def methodFactory(methodList, methodStr, localDict):
    'save a method or exec expression for each name in methodList'
    for methodName in methodList:
        if callable(methodStr):
            localDict[methodName] = methodStr
        else:
            localDict[methodName] = eval(methodStr % methodName)


def open_shelve(filename, mode=None, writeback=False, allowReadOnly=False,
                useHash=False, verbose=True):
    '''Alternative to shelve.open with several benefits:
- uses bsddb btree by default instead of bsddb hash, which is very slow
  for large databases.  Will automatically fall back to using bsddb hash
  for existing hash-based shelve files.  Set useHash=True to force it to use
  bsddb hash.

- allowReadOnly=True will automatically suppress permissions errors so
  user can at least get read-only access to the desired shelve, if no write
  permission.

- mode=None first attempts to open file in read-only mode, but if the file
  does not exist, opens it in create mode.

- raises standard exceptions defined in dbfile: WrongFormatError,
  PermissionsError, ReadOnlyError, NoSuchFileError

- avoids generating bogus __del__ warnings as Python shelve.open() does.
  '''
    if mode=='r': # READ-ONLY MODE, RAISE EXCEPTION IF NOT FOUND
        return dbfile.shelve_open(filename, flag=mode, useHash=useHash)
    elif mode is None:
        try: # 1ST TRY READ-ONLY, BUT IF NOT FOUND CREATE AUTOMATICALLY
            return dbfile.shelve_open(filename, 'r', useHash=useHash)
        except dbfile.NoSuchFileError:
            mode = 'c' # CREATE NEW SHELVE FOR THE USER
    try: # CREATION / WRITING: FORCE IT TO WRITEBACK AT close() IF REQUESTED
        return dbfile.shelve_open(filename, flag=mode, writeback=writeback,
                                  useHash=useHash)
    except dbfile.ReadOnlyError:
        if allowReadOnly:
            d = dbfile.shelve_open(filename, flag='r', useHash=useHash)
            if verbose:
                logger.warn('''
Opening shelve file %s in read-only mode because you lack
write permissions to this file.  You will NOT be able to modify the contents
of this shelve dictionary.  To avoid seeing this warning message,
use verbose=False argument for the classutil.open_shelve() function.
''' % filename)
            return d
        else:
            raise


def get_shelve_or_dict(filename=None, dictClass=None, **kwargs):
    if filename is not None:
        if dictClass is not None:
            return dictClass(filename, **kwargs)
        else:
            from mapping import IntShelve
            return IntShelve(filename, **kwargs)
    return {}


class PathSaver(object):

    def __init__(self, origPath):
        self.origPath = origPath
        self.origDir = os.getcwd()

    def __str__(self):
        if os.access(self.origPath, os.R_OK):
            return self.origPath
        trypath = os.path.join(self.origDir, self.origPath)
        if os.access(trypath, os.R_OK):
            return trypath


def override_rich_cmp(localDict):
    'create rich comparison methods that just use __cmp__'
    mycmp = localDict['__cmp__']
    localDict['__lt__'] = lambda self, other: mycmp(self, other) < 0
    localDict['__le__'] = lambda self, other: mycmp(self, other) <= 0
    localDict['__eq__'] = lambda self, other: mycmp(self, other) == 0
    localDict['__ne__'] = lambda self, other: mycmp(self, other) != 0
    localDict['__gt__'] = lambda self, other: mycmp(self, other) > 0
    localDict['__ge__'] = lambda self, other: mycmp(self, other) >= 0


class DBAttributeDescr(object):
    'obtain an attribute from associated db object'

    def __init__(self, attr):
        self.attr = attr

    def __get__(self, obj, objtype):
        return getattr(obj.db, self.attr)


def get_env_or_cwd(envname):
    'get the specified environment value or path to current directory'
    try:
        return os.environ[envname] # USER-SPECIFIED DIRECTORY
    except KeyError:
        return os.getcwd() # DEFAULT: SAVE IN CURRENT DIRECTORY


class RecentValueDictionary(WeakValueDictionary):
    '''keep the most recent n references in a WeakValueDictionary.
    This combines the elegant cache behavior of a WeakValueDictionary
    (only keep an item in cache if the user is still using it),
    with the most common efficiency pattern: locality, i.e.
    references to a given thing tend to cluster in time.  Note that
    this works *even* if the user is not holding a reference to
    the item between requests for it.  Our Most Recent queue will
    hold a reference to it, keeping it in the WeakValueDictionary,
    until it is bumped by more recent requests.

    n: the maximum number of objects to keep in the Most Recent queue,
       default value 50.'''

    def __init__(self, n=None):
        WeakValueDictionary.__init__(self)
        if n<1: # user doesn't want any Most Recent value queue
            self.__class__ = WeakValueDictionary # revert to regular WVD
            return
        if n is True: # assign default value
            self.n = 50
        else:
            self.n = int(n) # size limit
        self._head = self._tail = None
        self._keepDict = {} # most recent queue

    def __getitem__(self, k):
        v = WeakValueDictionary.__getitem__(self, k) # KeyError if not found
        self.keep_this(v)
        return v

    def _splice(self, previous, after):
        'link previous <--> after in queue, setting head & tail if needed'
        if previous is not None:
            self._keepDict[previous][1] = after
        if after is not None:
            self._keepDict[after][0] = previous
        elif previous is not None: # previous is end of queue!
            self._tail = previous
        if after is self._head:
            self._head = previous
            
    def keep_this(self, v):
        """add v as our most recent ref; drop oldest ref if over size limit.
        """
        if v is self._head:
            return # already at head of queue, so nothing to do
        try: # check if already in _keepDict
            previous, after = self._keepDict[v]
        except KeyError:
            self._keepDict[v] = [None, None]
        else: # remove from current position
            self._splice(previous, after)
            self._keepDict[v][0] = None
        self._splice(v, self._head) # place at head of queue
        if len(self._keepDict) > self.n: # delete oldest entry
            vdel = self._tail # get current tail
            self._splice(self._keepDict[vdel][0], None) # set new tail
            del self._keepDict[vdel]

    def __setitem__(self, k, v):
        WeakValueDictionary.__setitem__(self, k, v)
        self.keep_this(v)

    def clear(self):
        self._head = self._tail = None
        self._keepDict.clear()
        WeakValueDictionary.clear(self)

    def __repr__(self):
        return '<RecentValueDictionary object: %d members, cachesize %d>' %\
               (len(self._keepDict), self.n)


def make_attribute_interface(d):
    """
    If 'd' contains int values, use them to index tuples.

    If 'd' contains str values, use them to retrieve attributes from an obj.

    If d empty, use standard 'getattr'.
    """
    if len(d):
        v = d.values()[0]
        if isinstance(v, int):
            return AttrFromTuple(d)
        elif isinstance(v, str):
            return AttrFromObject(d)
        raise ValueError('dictionary values must be int or str!')

    return getattr


class AttrFromTuple(object):

    def __init__(self, attrDict):
        self.attrDict = attrDict

    def __call__(self, obj, attr, default=None):
        'getattr from tuple obj'
        try:
            return obj[self.attrDict[attr]]
        except (IndexError, KeyError):
            if default is not None:
                return default
        raise AttributeError("object has no attribute '%s'" % attr)


class AttrFromObject(AttrFromTuple):

    def __call__(self, obj, attr, default=None):
        'getattr with attribute name aliases'
        try:
            return getattr(obj, self.attrDict[attr])
        except KeyError:
            try:
                return getattr(obj, attr)
            except KeyError:
                if default is not None:
                    return default
        raise AttributeError("object has no attribute '%s'" % attr)


def kwargs_filter(kwargs, allowed):
    'return dictionary of kwargs filtered by list allowed'
    d = {}
    for arg in allowed:
        try:
            d[arg] = kwargs[arg]
        except KeyError:
            pass
    return d


def split_kwargs(kwargs, *targets):
    '''split kwargs into n+1 dicts for n targets; each target must
    be a list of arguments for that target'''
    kwargs = kwargs.copy()
    out = []
    for args in targets:
        d = {}
        for arg in args:
            try:
                d[arg] = kwargs[arg]
                del kwargs[arg]
            except KeyError:
                pass
        out.append(d)
    out.append(kwargs)
    return out

########NEW FILE########
__FILENAME__ = coordinator
from __future__ import generators
import os
import time
import thread
import sys
import xmlrpclib
import traceback
from SimpleXMLRPCServer import SimpleXMLRPCServer
import socket

import dbfile
import logging


def get_hostname(host=None):
    'get FQDN for host, or current host if not specified'
    if host is None:
        host = socket.gethostname()
    try:
        return socket.gethostbyaddr(host)[0]
    except socket.herror: # DNS CAN'T RESOLVE HOSTNAME
        return host # JUST USE HOSTNAME AS REPORTED BY gethostname()


def get_server(host, port, logRequests=False):
    """Start xmlrpc server on requested host:port.

    Return bound SimpleXMLRPCServer server obj and port it's bound to.

    Set port=0 to bind to a random port number.
    """
    if host is None: # use localhost as default
        host = 'localhost'
    server = SimpleXMLRPCServer((host, port), logRequests=logRequests)
    port = server.socket.getsockname()[1]
    logging.info("Running XMLRPC server on port %d..." % port)
    return server, port


class XMLRPCClientObject(object):
    """provides object proxy for remote object,
    with methods that mirror its xmlrpc_methods"""

    def __init__(self, server, name, methodDict):
        self.name = name
        self.server = server
        import new

        class methodcall(object):

            def __init__(self, name):
                self.name = name

            def __call__(self, obj, *args):
                return obj.server.server.methodCall(obj.name, self.name, args)

        # Create methods to access those of the remote object.
        for methodName in methodDict:
            setattr(self, methodName, new.instancemethod(methodcall(
                methodName), self, self.__class__))


class XMLRPCClient(dict):
    'interface to XMLRPC server serving multiple named objects'

    def __init__(self, url):
        self.server = xmlrpclib.ServerProxy(url)

    def __getitem__(self, name):
        'get connection to the named server object'
        try:
            return dict.__getitem__(self, name)
        except KeyError:
            # Get information about the requested object.
            methodDict = self.server.objectInfo(name)
            import types
            if isinstance(methodDict, types.StringType):
                raise KeyError(methodDict) # RETURNED VALUE IS ERROR MESSAGE!
            v = XMLRPCClientObject(self, name, methodDict)
            self[name] = v # SAVE THIS OBJECT INTO OUR DICTIONARY
            return v


class ConnectionDict(dict):
    """ensure that multiple requests for the same connection
    use the same ServerProxy"""

    def __call__(self, url, name):
        try:
            s = self[url] # REUSE EXISTING CONNECTION TO THE SERVER
        except KeyError:
            s = XMLRPCClient(url) # GET NEW CONNECTION TO THE SERVER
            self[url] = s # CACHE THIS CONNECTION
        return s[name] # GET THE REQUESTED OBJECT PROXY FROM THE SERVER

get_connection = ConnectionDict() # THIS RETURNS SAME ServerProxy FOR SAME url


def safe_dispatch(self, name, args):
    """restrict calls to selected methods, and trap all exceptions to
    keep server alive!"""
    import datetime
    if name in self.xmlrpc_methods:
        # Make sure this method is explicitly allowed.
        try: # TRAP ALL ERRORS TO PREVENT OUR SERVER FROM DYING
            print >>sys.stderr, 'XMLRPC:', name, args, \
                  datetime.datetime.now().isoformat(' ') # LOG THE REQUEST
            if self.xmlrpc_methods[name]: # use this as an alias for method
                m = getattr(self, self.xmlrpc_methods[name])
            else: # use method name as usual
                m = getattr(self, name) # GET THE BOUND METHOD
            val = m(*args) # CALL THE METHOD
            sys.stderr.flush() # FLUSH ANY OUTPUT TO OUR LOG
            return val # HAND BACK ITS RETURN VALUE
        except SystemExit:
            raise  # WE REALLY DO WANT TO EXIT.
        except: # METHOD RAISED AN EXCEPTION, SO PRINT TRACEBACK TO STDERR
            traceback.print_exc(self.max_tb, sys.stderr)
    else:
        print >>sys.stderr, "safe_dispatch: blocked unregistered method %s" \
                % name
    return False # THIS RETURN VALUE IS CONFORMABLE BY XMLRPC...


class ObjectFromString(list):
    """convenience class for initialization from string of format:
    val1,val2,foo=12,bar=39,sshopts=-1 -p 1234
    Args of format name=val are saved on the object as attributes;
    otherwise each arg is saved as a list.
    Argument type conversion is performed automatically if attrtype
    mapping provided either to constructor or by the class itself.
    Numeric keys in this mapping are applied to the corresponding
    list arguments; string keys in this mapping are applied to
    the corresponding attribute arguments.
    Both the argument separator and assignment separator can be
    customized."""
    _separator = ','
    _eq_separator = '='

    def __init__(self, s, separator=None, eq_separator=None):
        list.__init__(self)
        if separator is None:
            separator = self._separator
        if eq_separator is None:
            eq_separator = self._eq_separator
        args = s.split(separator)
        i = 0
        for arg in args:
            try: # PROCESS attr=val ARGUMENT FORMAT
                k, v = arg.split(eq_separator)
                try: # SEE IF WE HAVE A TYPE FOR THIS ATTRIBUTE
                    v = self._attrtype[k](v)
                except (AttributeError, KeyError):
                    pass # IF NO CONVERSION, JUST USE THE ORIGINAL STRING
                setattr(self, k, v) # SAVE VALUE AS ATTRIBUTE
            except ValueError: # JUST A SIMPLE ARGUMENT, SO SAVE AS ARG LIST
                try: # SEE IF WE HAVE A TYPE FOR THIS LIST ITEM
                    arg = self._attrtype[i](arg)
                except (AttributeError, KeyError):
                    pass # IF NO CONVERSION, JUST USE THE ORIGINAL STRING
                self.append(arg)
                i += 1 # ADVANCE OUR ARGUMENT COUNT


class FileDict(dict):
    """read key,value pairs as WS-separated lines,
    with objclass(value) conversion"""

    def __init__(self, filename, objclass=str):
        dict.__init__(self)
        f = file(filename, 'rU') # text file
        for line in f:
            key = line.split()[0] # GET THE 1ST ARGUMENT
            # Get the rest, strip the outer whitespace.
            val = line[len(key):].lstrip().rstrip()
            self[key] = objclass(val) # APPLY THE DESIRED TYPE CONVERSION
        f.close()


def detach_as_demon_process(self):
    "standard UNIX technique c/o Jurgen Hermann's Python Cookbook recipe"
    # CREATE AN APPROPRIATE ERRORLOG FILEPATH
    if not hasattr(self, 'errlog') or self.errlog is False:
        self.errlog = os.path.join(os.getcwd(), self.name + '.log')
    pid = os.fork()
    if pid:
        return pid

    os.setsid() # CREATE A NEW SESSION WITH NO CONTROLLING TERMINAL
    os.umask(0) # IS THIS ABSOLUTELY NECESSARY?

    sys.stdout = file(self.errlog, 'a') # Daemon sends all output to log file.
    sys.stderr = sys.stdout
    return 0


def serve_forever(self):
    'start the service -- this will run forever'
    import datetime
    print >>sys.stderr, "START_SERVER:%s %s" % (self.name, datetime.datetime.
                                                now().isoformat(' '))
    sys.stderr.flush()
    self.server.serve_forever()


class CoordinatorInfo(object):
    """stores information about individual coordinators for the controller
    and provides interface to Coordinator that protects against possibility of
    deadlock."""
    min_startup_time = 60.0

    def __init__(self, name, url, user, priority, resources, job_id=0,
                 immediate=False, demand_ncpu=0):
        self.name = name
        self.url = url
        self.user = user
        self.priority = priority
        self.job_id = job_id
        self.immediate = immediate
        self.server = xmlrpclib.ServerProxy(url)
        self.processors = {}
        self.resources = resources
        self.start_time = time.time()
        self.demand_ncpu = demand_ncpu # Set to non-zero for fixed #CPUs.
        self.allocated_ncpu = 0
        self.new_cpus = []
        self.last_start_proc_time = 0.0

    def __iadd__(self, newproc):
        "add a processor to this coordinator's list"
        self.processors[newproc] = time.time()
        return self

    def __isub__(self, oldproc):
        "remove a processor from this coordinator's list"
        del self.processors[oldproc]
        return self

    def update_load(self):
        """tell this coordinator to use only allocated_ncpu processors,
        and to launch processors on the list of new_cpus.
        Simply spawns a thread to do this without danger of deadlock"""
        import threading
        t = threading.Thread(target=self.update_load_thread,
                           args=(self.allocated_ncpu, self.new_cpus))
        self.new_cpus = [] # DISCONNECT FROM OLD LIST TO PREVENT OVERWRITING
        t.start()

    def update_load_thread(self, ncpu, new_cpus):
        """tell this coordinator to use only ncpu processors,
        and to launch processors on the list of new_cpus.
        Run this in a separate thread to prevent deadlock."""
        self.server.set_max_clients(ncpu)
        if len(new_cpus) > 0 and \
           time.time() - self.last_start_proc_time > self.min_startup_time:
            self.server.start_processors(new_cpus) # SEND OUR LIST
            self.last_start_proc_time = time.time()


class HostInfo(ObjectFromString):
    _attrtype = {'maxload': float}


class XMLRPCServerBase(object):
    'Base class for creating an XMLRPC server for multiple objects'
    xmlrpc_methods = {'methodCall': 0, 'objectList': 0, 'objectInfo': 0}
    max_tb = 10
    _dispatch = safe_dispatch # RESTRICT XMLRPC TO JUST THE METHODS LISTED HERE

    def __init__(self, name, host='', port=5000, logRequests=False,
                 server=None):
        self.host = host
        self.name = name
        if server is not None:
            self.server = server
            self.port = port
        else:
            self.server, self.port = get_server(host, port, logRequests)
        self.server.register_instance(self)
        self.objDict = {}

    def __setitem__(self, name, obj):
        'add a new object to serve'
        self.objDict[name] = obj

    def __delitem__(self, name):
        del self.objDict[name]

    def objectList(self):
        'get list of named objects in this server: [(name,methodDict),...]'
        return [(name, obj.xmlrpc_methods) for (name, obj) in
                self.objDict.items()]

    def objectInfo(self, objname):
        'get dict of methodnames on the named object'
        try:
            return self.objDict[objname].xmlrpc_methods
        except KeyError:
            return 'error: server has no object named %s' % objname

    def methodCall(self, objname, methodname, args):
        'run the named method on the named object and return its result'
        try:
            obj = self.objDict[objname]
            if methodname in obj.xmlrpc_methods:
                m = getattr(obj, methodname)
            else:
                print >>sys.stderr, \
                      "methodCall: blocked unregistered method %s" % methodname
                return ''
        except (KeyError, AttributeError):
            return '' # RETURN FAILURE CODE
        return m(*args) # RUN THE OBJECT METHOD

    def serve_forever(self, demonize=None, daemonize=False):
        'launch the XMLRPC service.  if daemonize=True, detach & exit.'
        if demonize is not None:
            logging.warning("demonize is a deprecated argument to \
                            serve_forever; use 'daemonize' instead!")
            daemonize = demonize

        print 'Serving on interface "%s", port %d' % (self.host, self.port, )

        if daemonize:
            print "detaching to run as a daemon."
            pid = detach_as_demon_process(self)
            if pid:
                print 'PID', pid
                sys.exit(0)

        serve_forever(self)

    def serve_in_thread(self):
        thread.start_new_thread(serve_forever, (self, ))

    def register(self, url=None, name='index', server=None):
        'register our server with the designated index server'
        data=self.registrationData # RAISE ERROR IF NO DATA TO REGISTER...
        if server is None and url is not None:
            # Use the URL to get the index server.
            server = get_connection(url, name)
        if server is not None:
            server.registerServer('%s:%d' % (self.host, self.port), data)
        else: # DEFAULT: SEARCH WORLDBASEPATH TO FIND INDEX SERVER
            from pygr import worldbase
            worldbase._mdb.registerServer('%s:%d' % (self.host, self.port),
                                          data)


class ResourceController(object):
    """Centralized controller for getting resources and rules for
    making them.
    """
    xmlrpc_methods = {'load_balance': 0, 'setrule': 0, 'delrule': 0,
                      'report_load': 0, 'register_coordinator': 0,
                      'unregister_coordinator': 0, 'register_processor': 0,
                      'unregister_processor': 0, 'get_resource': 0,
                      'acquire_rule': 0, 'release_rule': 0, 'request_cpus': 0,
                      'retry_unused_hosts': 0, 'get_status': 0,
                      'setthrottle': 0, 'del_lock': 0, 'get_hostinfo': 0,
                      'set_hostinfo': 0}
    _dispatch = safe_dispatch # RESTRICT XMLRPC TO JUST THE METHODS LISTED HERE
    max_tb = 10

    def __init__(self, rc='controller', port=5000, overload_margin=0.6,
                 rebalance_frequency=1200, errlog=False, throttle=1.0):
        self.name = rc
        self.overload_margin = overload_margin
        self.rebalance_frequency = rebalance_frequency
        self.errlog = errlog
        self.throttle = throttle
        self.rebalance_time = time.time()
        self.must_rebalance = False
        self.host = get_hostname()
        self.hosts = FileDict(self.name + '.hosts', HostInfo)
        self.getrules()
        self.getresources()
        self.server, self.port = get_server(self.host, port)
        self.server.register_instance(self)
        self.coordinators = {}
        self.njob = 0
        self.locks = {}
        self.systemLoad = {}
        hostlist=[host for host in self.hosts]
        for host in hostlist: # 1ST ASSUME HOST EMPTY, THEN GET LOAD REPORTS
            hostFQDN = get_hostname(host) # CONVERT ALL HOSTNAMES TO FQDNs
            if hostFQDN != host: # USE FQDN FOR ALL SUBSEQUENT REFS!
                self.hosts[hostFQDN] = self.hosts[host]
                del self.hosts[host]
            self.systemLoad[hostFQDN] = 0.0

    __call__ = serve_forever

    def assign_load(self):
        "calculate the latest balanced loads"
        maxload = 0.
        total = 0.
        current_job = 99999999
        for c in self.coordinators.values():
            if c.priority > 0.0 and c.job_id < current_job:
                current_job = c.job_id # FIND 1ST NON-ZER0 PRIORITY JOB
        for c in self.coordinators.values():
            if c.demand_ncpu: # DEMANDS A FIXED #CPUS, NO LOAD BALANCING
                c.run = True
            elif c.job_id == current_job or c.immediate:
                c.run = True # YES, RUN THIS JOB
                total += c.priority
            else:
                c.run=False
        for v in self.hosts.values(): # SUM UP TOTAL CPUS
            maxload += v.maxload
        maxload *= self.throttle # APPLY OUR THROTTLE CONTROL
        for c in self.coordinators.values(): #REMOVE DEMANDED CPUS
            if c.demand_ncpu:
                maxload -= c.demand_ncpu
        if maxload < 0.: # DON'T ALLOW NEGATIVE VALUES
            maxload = 0.
        if total > 0.: # DON'T DIVIDE BY ZERO...
            maxload /= float(total)
        for c in self.coordinators.values(): # ALLOCATE SHARE OF TOTAL CPUS...
            if c.demand_ncpu: # ALLOCATE EXACTLY THE NUMBER REQUESTED
                c.allocated_ncpu = int(c.demand_ncpu)
            elif c.run: # COMPUTE BASED ON PRIORITY SHARE
                c.allocated_ncpu = int(maxload * c.priority)
            else: # NOT RUNNING
                c.allocated_ncpu = 0
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def assign_processors(self):
        "hand out available processors to coordinators in order of need"
        margin = self.overload_margin - 1.0
        free_cpus = []
        nproc = {}
        for c in self.coordinators.values(): # COUNT NUMBER OF PROCS
            for host, pid in c.processors: # RUNNING ON EACH HOST
                try:
                    nproc[host] += 1.0 # INCREMENT AN EXISTING COUNT
                except KeyError:
                    nproc[host] = 1.0 # NEW, SO SET INITIAL COUNT
        for host in self.hosts: # BUILD LIST OF HOST CPUS TO BE ASSIGNED
            if host not in self.systemLoad: # ADDING A NEW HOST
                self.systemLoad[host] = 0.0 # DEFAULT LOAD: ASSUME HOST EMPTY
            try: # host MAY NOT BE IN nproc, SO CATCH THAT ERROR
                if self.systemLoad[host] > nproc[host]:
                    raise KeyError # USE self.systemLoad[host]
            except KeyError:
                load = self.systemLoad[host] # MAXIMUM VALUE
            else:
                load = nproc[host] # MAXIMUM VALUE
            if load < self.hosts[host].maxload + margin:
                free_cpus += int(self.hosts[host].maxload
                                 + self.overload_margin - load) * [host]
        if len(free_cpus) == 0: # WE DON'T HAVE ANY CPUS TO GIVE OUT
            return False
        l = [] # BUILD A LIST OF HOW MANY CPUS EACH COORDINATOR NEEDS
        for c in self.coordinators.values():
            ncpu = c.allocated_ncpu - len(c.processors)
            if ncpu > 0:
                l += ncpu*[c]  # ADD c TO l EXACTLY ncpu TIMES
        import random
        random.shuffle(l) # REORDER LIST OF COORDINATORS RANDOMLY
        i = 0 # INDEX INTO OUR l LIST
        while i < len(free_cpus) and i < len(l):
            # Hand out free CPUs one by one.
            l[i].new_cpus.append(free_cpus[i])
            i += 1
        return i > 0 # RETURN TRUE IF WE HANDED OUT SOME PROCESSORS

    def load_balance(self):
        "recalculate load assignments, and assign free cpus"
        self.rebalance_time = time.time() # RESET OUR FLAGS
        self.must_rebalance = False
        # Calculate how many CPUs each coordinator should get.
        self.assign_load()
        # Assign free CPUs to coordinators which need them.
        self.assign_processors()
        for c in self.coordinators.values():
            c.update_load() # INFORM THE COORDINATOR
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def get_hostinfo(self, host, attr):
        "get a host attribute"
        return getattr(self.hosts[host], attr)

    def set_hostinfo(self, host, attr, val):
        "increase or decrease the maximum load allowed on a given host"
        try:
            setattr(self.hosts[host], attr, val)
        except KeyError:
            self.hosts[host] = HostInfo('%s=%s' % (attr, str(val)))
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def getrules(self):
        import shelve
        self.rules = dbfile.shelve_open(self.name + '.rules')

    def getresources(self):
        import shelve
        self.resources = dbfile.shelve_open(self.name + '.rsrc')

    def setrule(self, rsrc, rule):
        "save a resource generation rule into our database"
        self.rules[rsrc] = rule
        self.rules.close() # THIS IS THE ONLY WAY I KNOW TO FLUSH...
        self.getrules()
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def delrule(self, rsrc):
        "delete a resource generation rule from our database"
        try:
            del self.rules[rsrc]
        except KeyError:
            print >>sys.stderr, "Attempt to delete unknown resource rule %s" \
                    % rsrc
        else:
            self.rules.close() # THIS IS THE ONLY WAY I KNOW TO FLUSH...
            self.getrules()
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def setthrottle(self, throttle):
        "set the total level of usage of available CPUs, usually 1.0"
        self.throttle = float(throttle)
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def report_load(self, host, pid, load):
        "save a reported load from one of our processors"
        self.systemLoad[host] = load
        # AT A REGULAR INTERVAL WE SHOULD REBALANCE LOAD
        if self.must_rebalance or \
               time.time() - self.rebalance_time > self.rebalance_frequency:
            self.load_balance()
        if load < self.hosts[host].maxload + self.overload_margin:
            return True  # OK TO CONTINUE
        else:
            return False # THIS SYSTEM OVERLOADED, TELL PROCESSOR TO EXIT

    def register_coordinator(self, name, url, user, priority, resources,
                             immediate, demand_ncpu):
        "save a coordinator's registration info"
        try:
            print >>sys.stderr, 'change_priority: %s (%s,%s): %f -> %f' \
                  % (name, user, url, self.coordinators[url].priority,
                     priority)
            self.coordinators[url].priority = priority
            self.coordinators[url].immediate = immediate
            self.coordinators[url].demand_ncpu = demand_ncpu
        except KeyError:
            print >>sys.stderr, 'register_coordinator: %s (%s,%s): %f' \
                  % (name, user, url, priority)
            self.coordinators[url] = CoordinatorInfo(name, url, user, priority,
                                                     resources, self.njob,
                                                     immediate, demand_ncpu)
            self.njob += 1 # INCREMENT COUNT OF JOBS WE'VE REGISTERED
        self.must_rebalance = True # FORCE REBALANCING ON NEXT OPPORTUNITY
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def unregister_coordinator(self, name, url, message):
        "remove a coordinator from our list"
        try:
            del self.coordinators[url]
            print >>sys.stderr, 'unregister_coordinator: %s (%s): %s' \
                  % (name, url, message)
            self.load_balance() # FORCE IT TO REBALANCE THE LOAD TO NEW JOBS...
        except KeyError:
            print >>sys.stderr, 'unregister_coordinator: %s unknown:%s (%s)' \
                  % (name, url, message)
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def request_cpus(self, name, url):
        "return a list of hosts for this coordinator to run processors on"
        try:
            c = self.coordinators[url]
        except KeyError:
            print >>sys.stderr, 'request_cpus: unknown coordinator %s @ %s' \
                    % (name, url)
            return [] # HAND BACK AN EMPTY LIST
        # Calculate how many CPUs each coordinator should get.
        self.assign_load()
        # Assign free CPUs to coordinators which need them.
        self.assign_processors()
        new_cpus=tuple(c.new_cpus) # MAKE A NEW COPY OF THE LIST OF HOSTS
        del c.new_cpus[:] # EMPTY OUR LIST
        return new_cpus

    def register_processor(self, host, pid, url):
        "record a new processor starting up"
        try:
            self.coordinators[url] += (host, pid)
            self.systemLoad[host] += 1.0 # THIS PROBABLY INCREASES LOAD BY 1
        except KeyError:
            pass
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def unregister_processor(self, host, pid, url):
        "processor shutting down, so remove it from the list"
        try:
            self.coordinators[url] -= (host, pid)
            self.systemLoad[host] -= 1.0 # THIS PROBABLY DECREASES LOAD BY 1
            if self.systemLoad[host] < 0.0:
                self.systemLoad[host] = 0.0
            for k, v in self.locks.items(): # MAKE SURE THIS PROC HAS NO LOCKS
                h = k.split(':')[0]
                if h == host and v == pid:
                    del self.locks[k] # REMOVE ALL ITS PENDING LOCKS
        except KeyError:
            pass
        self.load_balance() # FREEING A PROCESSOR, SO REBALANCE TO USE THIS
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def get_resource(self, host, pid, rsrc):
        """return a filename for the resource, or False if rule must be
        applied, or True if client must wait to get the resource"""
        key = host + ':' + rsrc
        try: # JUST HAND BACK THE RESOURCE
            return self.resources[key]
        except KeyError:
            if key in self.locks:
                return True # TELL CLIENT TO WAIT
            else:
                return False # TELL CLIENT TO ACQUIRE IT VIA RULE

    def acquire_rule(self, host, pid, rsrc):
        """lock the resource on this specific host
        and return its production rule"""
        if rsrc not in self.rules:
            return False # TELL CLIENT NO SUCH RULE
        key = host + ':' + rsrc
        if key in self.locks:
            return True # TELL CLIENT TO WAIT
        # Lock this resource on this host until constructed.
        self.locks[key] = pid
        return self.rules[rsrc] # RETURN THE CONSTRUCTION RULE

    def release_rule(self, host, pid, rsrc):
        """client is done applying this rule, it is now safe
        to give out the resource"""
        key = host + ':' + rsrc
        self.del_lock(host, rsrc)
        # Add the file name to resource list.
        self.resources[key] = self.rules[rsrc][0]
        self.resources.close() # THIS IS THE ONLY WAY I KNOW TO FLUSH THIS...
        self.getresources()
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def del_lock(self, host, rsrc):
        "delete a lock on a pending resource construction process"
        key = host + ':' + rsrc
        try:
            del self.locks[key] # REMOVE THE LOCK
        except KeyError:
            print >> sys.stderr, "attempt to release non-existent lock \
                    %s,%s:%d" % (host, rule, pid)
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def retry_unused_hosts(self):
        "reset systemLoad for hosts that have no jobs running"
        myhosts = {}
        for c in self.coordinators.values(): # LIST HOSTS WE'RE CURRENTLY USING
            for host, pid in c.processors:
                myhosts[host] = None # MARK THIS HOST AS IN USE
        for host in self.systemLoad: # RESET LOAD FOR ALL HOSTS WE'RE NOT USING
            if host not in myhosts:
                self.systemLoad[host] = 0.0
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def get_status(self):
        """get report of system loads, max loads, coordinators, rules,
        resources, locks"""
        l = [(name, host.maxload) for name, host in self.hosts.items()]
        l.sort()
        return self.name, self.errlog, self.systemLoad, l, \
               [(c.name, c.url, c.priority, c.allocated_ncpu,
                 len(c.processors), c.start_time) for c in
                self.coordinators.values()], dict(self.rules), \
                dict(self.resources), self.locks


class AttrProxy(object):

    def __init__(self, getattr_proxy, k):
        self.getattr_proxy = getattr_proxy
        self.k = k

    def __getattr__(self, attr):
        try:
            val = self.getattr_proxy(self.k, attr) # GET IT FROM OUR PROXY
        except:
            raise AttributeError('unable to get proxy attr ' + attr)
        setattr(self, attr, val) # CACHE THIS ATTRIBUTE RIGHT HERE!
        return val


class DictAttrProxy(dict):

    def __init__(self, getattr_proxy):
        dict.__init__(self)
        self.getattr_proxy = getattr_proxy

    def __getitem__(self, k):
        try:
            return dict.__getitem__(self, k)
        except KeyError:
            val = AttrProxy(self.getattr_proxy, k)
            self[k] = val
            return val


class Coordinator(object):
    """Run our script as Processor on one or more client nodes, using
    XMLRPC communication between clients and server.
    On the server all output is logged to name.log,
    and successfully completed task IDs are stored in name.success,
    and error task IDs are stored in name.error
    On the clients all output is logged to the file name_#.log in the user's
    and/or system-specific temporary directory."""
    xmlrpc_methods = {'start_processors': 0, 'register_client': 0,
                      'unregister_client': 0, 'report_success': 0,
                      'report_error': 0, 'next': 0, 'get_status': 0,
                      'set_max_clients': 0, 'stop_client': 0}
    _dispatch = safe_dispatch # RESTRICT XMLRPC TO JUST THE METHODS LISTED HERE
    max_tb = 10 # MAXIMUM #STACK LEVELS TO PRINT IN TRACEBACKS
    max_ssh_errors = 5 #MAXIMUM #ERRORS TO PERMIT IN A ROW BEFORE QUITTING
    python = 'python' # DEFAULT EXECUTABLE FOR RUNNING OUR CLIENTS

    def __init__(self, name, script, it, resources, port=8888, priority=1.0,
                 rc_url=None, errlog=False, immediate=False,
                 ncpu_limit=999999, demand_ncpu=0, max_initialization_errors=3,
                 **kwargs):
        self.name = name
        self.script = script
        self.it = iter(it) # Make sure self.it is an iterator.
        self.resources = resources
        self.priority = priority
        self.errlog = errlog
        self.immediate = immediate
        self.ncpu_limit = ncpu_limit
        self.demand_ncpu = demand_ncpu
        self.max_initialization_errors = max_initialization_errors
        self.kwargs = kwargs
        self.host = get_hostname()
        self.user = os.environ['USER']
        try:
            # Make sure ssh-agent is available before we launch
            # a lot of processes.
            a = os.environ['SSH_AGENT_PID']
        except KeyError:
            raise OSError(1, 'SSH_AGENT_PID not found. No ssh-agent running?')
        self.dir = os.getcwd()
        self.n = 0
        self.nsuccess = 0
        self.nerrors = 0
        self.nssh_errors = 0
        self.iclient = 0
        self.max_clients = 40
        if rc_url is None:
            # Try the default resource-controller address on the same host.
            rc_url = 'http://%s:5000' % self.host
        self.rc_url = rc_url
        # Connect to the resource controller...
        self.rc_server = xmlrpclib.ServerProxy(rc_url)
        # ...create an XMLRPC server.
        self.server, self.port = get_server(self.host, port)
        # ...and provide it with all the methods.
        self.server.register_instance(self)
        self.clients = {}
        self.pending = {}
        self.already_done = {}
        self.stop_clients = {}
        self.logfile = {}
        self.clients_starting = {}
        self.clients_initializing = {}
        self.initialization_errors = {}
        try: # LOAD LIST OF IDs ALREADY SUCCESSFULLY PROCESSED, IF ANY
            f = file(name + '.success', 'rU') # text file
            for line in f:
                self.already_done[line.strip()] = None
            f.close()
        except IOError: # OK IF NO SUCCESS FILE YET, WE'LL CREATE ONE.
            pass
        # Success file is to be cumulative but overwrite the error file.
        self.successfile = file(name + '.success', 'a')
        self.errorfile = file(name + '.error', 'w')
        self.done = False
        self.hosts = DictAttrProxy(self.rc_server.get_hostinfo)
        self.register()

    def __call__(self, *l, **kwargs):
        "start the server, and launch a cpu request in a separate thread"
        import threading
        t = threading.Thread(target=self.initialize_thread)
        t.start()
        serve_forever(self, *l, **kwargs)

    def initialize_thread(self):
        """run this method in a separate thread
        to bootstrap our initial cpu request"""
        time.sleep(5) # GIVE serve_forever() TIME TO START SERVER
        # Now ask the controller to rebalance and give up CPUs.
        self.rc_server.load_balance()

    def start_client(self, host):
        "start a processor on a client node"
        import tempfile
        if len(self.clients) >= self.ncpu_limit:
            print >>sys.stderr, 'start_client: blocked, CPU limit', \
                  len(self.clients), self.ncpu_limit
            return # DON'T START ANOTHER PROCESS, TOO MANY ALREADY
        if len(self.clients) >= self.max_clients:
            print >>sys.stderr, 'start_client: blocked, too many already', \
                  len(self.clients), self.max_clients
            return # DON'T START ANOTHER PROCESS, TOO MANY ALREADY
        try:
            if len(self.clients_starting[host]) >= self.max_ssh_errors:
                print >>sys.stderr, \
                      'start_client: blocked, too many unstarted jobs:', \
                      host, self.clients_starting[host]
                return # DON'T START ANOTHER PROCESS, host MAY BE DEAD...
        except KeyError: # NO clients_starting ON host, GOOD!
            pass
        try:
            if len(self.initialization_errors[host]) >= \
               self.max_initialization_errors:
                print >>sys.stderr, 'start_client: blocked, too many \
                        initialization errors:', host, \
                        self.initialization_errors[host]
                return # DON'T START ANOTHER PROCESS, host HAS A PROBLEM
        except KeyError: # NO initialization_errors ON host, GOOD!
            pass
        try:
            sshopts = self.hosts[host].sshopts # GET sshopts VIA XMLRPC
        except AttributeError:
            sshopts = ''
        logfile = os.path.join(tempfile.gettempdir(), '%s_%d.log' \
                               % (self.name, self.iclient))
        # PASS OUR KWARGS ON TO THE CLIENT PROCESSOR
        kwargs = ' '.join(['--%s=%s' % (k, v) for k, v in self.kwargs.items()])
        cmd = 'cd %s;%s %s --url=http://%s:%d --rc_url=%s --logfile=%s %s %s' \
             % (self.dir, self.python, self.script, self.host, self.port,
                self.rc_url, logfile, self.name, kwargs)
        # UGH, HAVE TO MIX CSH REDIRECTION (REMOTE) WITH SH REDIRECTION (LOCAL)
        ssh_cmd = "ssh %s %s '(%s) </dev/null >&%s &' </dev/null >>%s 2>&1 &" \
                 % (sshopts, host, cmd, logfile, self.errlog)
        print >>sys.stderr, 'SSH: ' + ssh_cmd
        self.logfile[logfile] = [host, False, self.iclient] # NO PID YET
        try: # RECORD THIS CLIENT AS STARTING UP
            self.clients_starting[host][self.iclient] = time.time()
        except KeyError: # CREATE A NEW HOST ENTRY
            self.clients_starting[host] = {self.iclient: time.time()}
        # RUN SSH IN BACKGROUND TO AVOID WAITING FOR IT TO TIMEOUT!!!
        os.system(ssh_cmd) # LAUNCH THE SSH PROCESS, SHOULD RETURN IMMEDIATELY
        self.iclient += 1 # ADVANCE OUR CLIENT COUNTER

    def start_processors(self, hosts):
        "start processors on the list of hosts using SSH transport"
        for host in hosts: # LAUNCH OURSELVES AS PROCESSOR ON ALL THESE HOSTS
            self.start_client(host)
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def register(self):
        "register our existence with the resource controller"
        url = 'http://%s:%d' % (self.host, self.port)
        self.rc_server.register_coordinator(self.name, url, self.user,
                                            self.priority, self.resources,
                                            self.immediate, self.demand_ncpu)

    def unregister(self, message):
        "tell the resource controller we're exiting"
        url = 'http://%s:%d' % (self.host, self.port)
        self.rc_server.unregister_coordinator(self.name, url, message)

    def register_client(self, host, pid, logfile):
        'XMLRPC call to register client hostname and PID as starting_up'
        print >>sys.stderr, 'register_client: %s:%d' % (host, pid)
        self.clients[(host, pid)] = 0
        try:
            self.logfile[logfile][1] = pid # SAVE OUR PID
            iclient = self.logfile[logfile][2] # GET ITS CLIENT ID
            del self.clients_starting[host][iclient] #REMOVE FROM STARTUP LIST
        except KeyError:
            print >>sys.stderr, 'no client logfile?', host, pid, logfile
        self.clients_initializing[(host, pid)] = logfile
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def unregister_client(self, host, pid, message):
        'XMLRPC call to remove client from register as exiting'
        print >>sys.stderr, 'unregister_client: %s:%d %s' \
                % (host, pid, message)
        try:
            del self.clients[(host, pid)]
        except KeyError:
            print >>sys.stderr, 'unregister_client: unknown client %s:%d' \
                    % (host, pid)
        try: # REMOVE IT FROM THE LIST OF CLIENTS TO SHUTDOWN, IF PRESENT
            del self.stop_clients[(host, pid)]
        except KeyError:
            pass
        try: # REMOVE FROM INITIALIZATION LIST
            del self.clients_initializing[(host, pid)]
        except KeyError:
            pass
        if len(self.clients) == 0 and self.done:
            # No more tasks or clients, the server can exit.
            self.exit("Done")
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def report_success(self, host, pid, success_id):
        'mark task as successfully completed'
        # Keep permanent record of success ID.
        print >>self.successfile, success_id
        self.successfile.flush()
        self.nsuccess += 1
        try:
            self.clients[(host, pid)] += 1
        except KeyError:
            print >>sys.stderr, 'report_success: unknown client %s:%d' \
                    % (host, pid)
        try:
            del self.pending[success_id]
        except KeyError:
            print >>sys.stderr, 'report_success: unknown ID %s' \
                    % str(success_id)
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def report_error(self, host, pid, id, tb_report):
        "get traceback report from client as text"
        print >>sys.stderr, "TRACEBACK: %s:%s ID %s\n%s" % \
              (host, str(pid), str(id), tb_report)
        if (host, pid) in self.clients_initializing:
            logfile = self.clients_initializing[(host, pid)]
            try:
                self.initialization_errors[host].append(logfile)
            except KeyError:
                self.initialization_errors[host] = [logfile]
        try:
            del self.pending[id]
        except KeyError:
            # Not associated with an actual task ID, do not record.
            if id is not None and id is not False:
                print >>sys.stderr, 'report_error: unknown ID %s' % str(id)
        else:
            print >>self.errorfile, id # KEEP PERMANENT RECORD OF FAILURE ID
            self.nerrors += 1
            self.errorfile.flush()
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def next(self, host, pid, success_id):
        'return next ID from iterator to the XMLRPC caller'
        if (host, pid) not in self.clients:
            print >>sys.stderr, 'next: unknown client %s:%d' % (host, pid)
            return False # HAND BACK "NO MORE FOR YOU TO DO" SIGNAL
        try: # INITIALIZATION DONE, SO REMOVE FROM INITIALIZATION LIST
            del self.clients_initializing[(host, pid)]
        except KeyError:
            pass
        if success_id is not False:
            self.report_success(host, pid, success_id)
        if self.done: # EXHAUSTED OUR ITERATOR, SO SHUT DOWN THIS CLIENT
            return False # HAND BACK "NO MORE FOR YOU TO DO" SIGNAL
        try:  # CHECK LIST FOR COMMAND TO SHUT DOWN THIS CLIENT
            del self.stop_clients[(host, pid)] # IS IT IN stop_clients?
            return False # IF SO, HAND BACK "NO MORE FOR YOU TO DO" SIGNAL
        except KeyError: # DO ONE MORE CHECK: ARE WE OVER OUR MAX ALLOWED LOAD?
            if len(self.clients) > self.max_clients:
                # Yes, better throttle down.
                print >>sys.stderr, 'next: halting %s:too many processors \
                        (%d>%d)' % (host, len(self.clients), self.max_clients)
                return False # HAND BACK "NO MORE FOR YOU TO DO" SIGNAL
        for id in self.it: # GET AN ID WE CAN USE
            if str(id) not in self.already_done:
                self.n += 1 # GREAT, WE CAN USE THIS ID
                self.lastID = id
                self.pending[id] = (host, pid, time.time())
                print >>sys.stderr, 'giving id %s to %s:%d' % (str(id),
                                                               host, pid)
                return id
        print >>sys.stderr, 'exhausted all items from iterator!'
        self.done = True # EXHAUSTED OUR ITERATOR
        # Release our claims on any further processor allication
        # and inform the resource controller about it.
        self.priority = 0.0
        self.register()
        return False # False IS CONFORMABLE BY XMLRPC...

    def get_status(self):
        "return basic status info on number of jobs finished, client list etc."
        client_report = [client + (nsuccess, ) for client, nsuccess
                         in self.clients.items()]
        pending_report = [(k, ) + v for k, v in self.pending.items()]
        return self.name, self.errlog, self.n, self.nsuccess, self.nerrors, \
                client_report, pending_report, self.logfile

    def set_max_clients(self, n):
        "change the maximum number of clients we should have running"
        self.max_clients = int(n)  # MAKE SURE n IS CONVERTABLE TO int
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def stop_client(self, host, pid):
        "set signal forcing this client to exit on next iteration"
        self.stop_clients[(host, pid)] = None
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def exit(self, message):
        "clean up and close this server"
        self.unregister(message)
        self.successfile.close()
        self.errorfile.close()
        sys.exit()


try:

    class ResourceFile(file):
        """wrapper around some locking behavior, to ensure only one
        copy operation performed for a given resource on a given host.
        Otherwise, it's just a regular file object."""

        def __init__(self, resource, rule, mode, processor):
            "resource is name of the resource; rule is (localFile, cpCommand)"
            self.resource = resource
            self.processor = processor
            localFile, cpCommand = rule
            if not os.access(localFile, os.R_OK):
                cmd = cpCommand % localFile
                print 'copying data:', cmd
                os.system(cmd)
            # Now, initialise as a real file object.
            file.__init__(self, localFile, mode)

        def close(self):
            # Release the lock we placed on this rule.
            self.processor.release_rule(self.resource)
            file.close(self)
except TypeError:
    pass


class Processor(object):
    'provides an iterator interface to an XMLRPC ID server'
    max_errors_in_a_row = 10 # LOOKS LIKE NOTHING WORKS HERE, SO QUIT!
    max_tb = 10 # DON'T SHOW MORE THAN 10 STACK LEVELS FOR A TRACEBACK
    report_frequency = 600
    overload_max = 5 # Max number of overload events in a row before we exit.

    def __init__(self, url = "http://localhost:8888",
                 rc_url = 'http://localhost:5000', logfile=False, **kwargs):
        self.url = url
        self.logfile = logfile
        self.server = xmlrpclib.ServerProxy(url)
        self.rc_url = rc_url
        self.rc_server = xmlrpclib.ServerProxy(rc_url)
        self.host = get_hostname()
        self.pid = os.getpid()
        self.user = os.environ['USER']
        self.success_id = False
        self.pending_id = False
        self.exit_message = 'MYSTERY-EXIT please debug'
        self.overload_count = 0

    def register(self):
        "add ourselves to list of processors for this server"
        self.server.register_client(self.host, self.pid, self.logfile)
        self.rc_server.register_processor(self.host, self.pid, self.url)
        print >>sys.stderr, 'REGISTERED:', self.url, self.rc_url

    def unregister(self, message):
        "remove ourselves from list of processors for this server"
        if self.success_id is not False: # REPORT THAT LAST JOB SUCCEEDED!
            self.report_success(self.success_id)
        self.server.unregister_client(self.host, self.pid, message)
        self.rc_server.unregister_processor(self.host, self.pid, self.url)
        print >>sys.stderr, 'UNREGISTERED:', self.url, self.rc_url, message

    def __iter__(self):
        return self

    def next(self):
        "get next ID from server"
        # REPORT LAST JOB SUCCESSFULLY COMPLETED, IF ANY
        while 1:
            id = self.server.next(self.host, self.pid, self.success_id)
            self.success_id = False # ERASE SUCCESS ID
            if id is True: # WE'RE BEING TOLD TO JUST WAIT
                time.sleep(60) # SO GO TO SLEEP FOR A MINUTE
            else:
                break
        if id is False: # NO MODE id FOR US TO PROCESS, SO QUIT
            self.serverStopIteration = True # RECORD THIS AS GENUINE END EVENT
            raise StopIteration
        else: # HAND BACK THE id TO THE USER
            self.pending_id = id
            return id

    def report_success(self, id):
        "report successful completion of task ID"
        self.server.report_success(self.host, self.pid, id)

    def report_error(self, id):
        "report an error using traceback.print_exc()"
        import StringIO
        err_report = StringIO.StringIO()
        traceback.print_exc(self.max_tb, sys.stderr) #REPORT TB TO OUR LOG
        traceback.print_exc(self.max_tb, err_report) #REPORT TB TO SERVER
        self.server.report_error(self.host, self.pid, id,
                                 err_report.getvalue())
        err_report.close()

    def report_load(self):
        "report system load"
        load = os.getloadavg()[0] # GET 1 MINUTE LOAD AVERAGE
        if self.rc_server.report_load(self.host, self.pid, load) is False:
            # Are we consistently overloaded for an extended time period?
            self.overload_count += 1
            if self.overload_count > self.overload_max:
                # Limit exceeded, exit.
                self.exit('load too high')
        else:
            self.overload_count = 0

    def open_resource(self, resource, mode):
        "get a file object for the requested resource, opened in mode"
        while 1:
            rule = self.rc_server.get_resource(self.host, self.pid, resource)
            if rule is False: # WE HAVE TO LOCK AND APPLY A RULE...
                rule = self.acquire_rule(resource)
                if rule is True:
                    # Looks like a race condition, wait a minute before
                    # trying again.
                    time.sleep(60)
                    continue
                # Construct the resource.
                return ResourceFile(resource, rule, mode, self)
            elif rule is True:
                # Rule is locked by another processor, wait a minute before
                # trying again.
                time.sleep(60)
            else: # GOT A REGULAR FILE, SO JUST OPEN IT
                return file(rule, mode)

    def acquire_rule(self, resource):
        """lock the specified resource rule for this host
        so that it's safe to build it"""
        rule = self.rc_server.acquire_rule(self.host, self.pid, resource)
        if rule is False: # NO SUCH RESOURCE?!?
            self.exit('invalid resource: ' + resource)
        return rule

    def release_rule(self, resource):
        "release our lock on this resource rule, so others can use it"
        self.rc_server.release_rule(self.host, self.pid, resource)

    def exit(self, message):
        "save message for self.unregister() and force exit"
        self.exit_message = message
        raise SystemExit

    def run_all(self, resultGenerator, **kwargs):
        "run until all task IDs completed, trap & report all errors"
        errors_in_a_row = 0
        it = resultGenerator(self, **kwargs) # GET ITERATOR FROM GENERATOR
        report_time = time.time()
        self.register() # REGISTER WITH RESOURCE CONTROLLER & COORDINATOR
        initializationError = None
        try: # TRAP ERRORS BOTH IN USER CODE AND coordinator CODE
            while 1:
                try: # TRAP AND REPORT ALL ERRORS IN USER CODE
                    id = it.next() # THIS RUNS USER CODE FOR ONE ITERATION
                    self.success_id = id  # MARK THIS AS A SUCCESS...
                    errors_in_a_row = 0
                    initializationError = False
                except StopIteration: # NO MORE TASKS FOR US...
                    if not hasattr(self, 'serverStopIteration'): # Weird!
                        # USER CODE RAISED StopIteration?!?
                        self.report_error(self.pending_id) # REPORT THE PROBLEM
                        self.exit_message = 'user StopIteration error'
                    elif initializationError:
                        self.exit_message = 'initialization error'
                    else:
                        self.exit_message = 'done'
                    break
                except SystemExit: # sys.exit() CALLED
                    raise  # WE REALLY DO WANT TO EXIT.
                except: # MUST HAVE BEEN AN ERROR IN THE USER CODE
                    if initializationError is None: # STILL IN INITIALIZATION
                        initializationError=True
                    self.report_error(self.pending_id) # REPORT THE PROBLEM
                    errors_in_a_row +=1
                    if errors_in_a_row>=self.max_errors_in_a_row:
                        self.exit_message='too many errors'
                        break
                if time.time()-report_time>self.report_frequency:
                    self.report_load() # SEND A ROUTINE LOAD REPORT
                    report_time=time.time()
        except SystemExit: # sys.exit() CALLED
            pass  # WE REALLY DO WANT TO EXIT.
        except: # IMPORTANT TO TRAP ALL ERRORS SO THAT WE UNREGISTER!!
            traceback.print_exc(self.max_tb, sys.stderr) #REPORT TB TO OUR LOG
            self.exit_message='error trap'
        self.unregister('run_all '+self.exit_message) # MUST UNREGISTER!!

    def run_interactive(self, it, n=1, **kwargs):
        "run n task IDs, with no error trapping"
        if not hasattr(it, 'next'):
            # Assume 'it' is a generator, use it to get an iterator.
            it = it(self, **kwargs)
        i=0
        self.register() # REGISTER WITH RESOURCE CONTROLLER & COORDINATOR
        try: # EVEN IF ERROR OCCURS, WE MUST UNREGISTER!!
            for id in it:
                self.success_id=id
                i+=1
                if i>=n:
                    break
        except:
            self.unregister('run_interactive error') # MUST UNREGISTER!!!
            raise # SHOW THE ERROR INTERACTIVELY
        self.unregister('run_interactive exit')
        return it # HAND BACK ITERATOR IN CASE USER WANTS TO RUN MORE...


def parse_argv():
    """parse sys.argv into a dictionary of GNU-style args (--foo=bar)
    and a list of other args"""
    d = {}
    l = []
    for v in sys.argv[1:]:
        if v[:2] == '--':
            try:
                k, v = v[2:].split('=')
                d[k] = v
            except ValueError:
                d[v[2:]] = None
        else:
            l.append(v)
    return d, l


def start_client_or_server(clientGenerator, serverGenerator, resources,
                           script):
    """start controller, client or server depending on whether
    we get coordinator argument from the command-line args.

    Client must be a generator function that takes Processor as argument,
    and uses it as an iterator.
    Also, clientGenerator must yield the IDs that the Processor provides
    (this structure allows us to trap all exceptions from clientGenerator,
    while allowing it to do resource initializations that would be
    much less elegant in a callback function.)

    Server must be a function that returns an iterator (e.g. a generator).
    Resources is a list of strings naming the resources we need
    copied to local host for client to be able to do its work.

    Both client and server constructors use **kwargs to get command
    line arguments (passed as GNU-style --foo=bar;
    see the constructor arguments to see the list of
    options that each can be passed.

    #CALL LIKE THIS FROM yourscript.py:
    import coordinator
    if __name__ == '__main__':
      coordinator.start_client_or_server(clientGen, serverGen,
        resources,__file__)

    To start the resource controller:
      python coordinator.py --rc=NAME [options]

    To start a job coordinator:
      python yourscript.py NAME [--rc_url=URL] [options]

    To start a job processor:
      python yourscript.py --url=URL --rc_url=URL [options]"""
    d, l = parse_argv()
    if 'url' in d: # WE ARE A CLIENT!
        client = Processor(**d)
        time.sleep(5) # GIVE THE SERVER SOME BREATHING SPACE
        client.run_all(clientGenerator, **d)
    elif 'rc' in d: # WE ARE THE RESOURCE CONTROLLER
        rc_server = ResourceController(**d) # NAME FOR THIS CONTROLLER...
        detach_as_demon_process(rc_server)
        rc_server() # START THE SERVER
    else: # WE ARE A SERVER
        try: # PASS OUR KWARGS TO THE SERVER FUNCTION
            it = serverGenerator(**d)
        except TypeError: # DOESN'T WANT ANY ARGS?
            it = serverGenerator()
        server = Coordinator(l[0], script, it, resources, **d)
        detach_as_demon_process(server)
        server() # START THE SERVER


class CoordinatorMonitor(object):
    "Monitor a Coordinator."

    def __init__(self, coordInfo):
        self.name, self.url, self.priority, self.allocated_ncpu, \
                self.ncpu, self.start_time = coordInfo
        self.server = xmlrpclib.ServerProxy(self.url)
        self.get_status()

    def get_status(self):
        self.name, self.errlog, self.n, self.nsuccess, self.nerrors, \
                self.client_report, self.pending_report, \
                self.logfile = self.server.get_status()
        print "Got status from Coordinator: ", self.name, self.url

    def __getattr__(self, attr):
        "just pass on method requests to our server"
        return getattr(self.server, attr)


class RCMonitor(object):
    """monitor a ResourceController.  Useful methods:
    get_status()
    load_balance()
    setrule(rsrc,rule)
    delrule(rsrc)
    setload(host,maxload)
    retry_unused_hosts()
    Documented in ResourceController docstrings."""

    def __init__(self, host=None, port=5000):
        host = get_hostname(host) # GET FQDN
        self.rc_url = 'http://%s:%d' % (host, port)
        self.rc_server = xmlrpclib.ServerProxy(self.rc_url)
        self.get_status()

    def get_status(self):
        self.name, self.errlog, self.systemLoad, self.hosts, \
                coordinators, self.rules, self.resources, \
                self.locks = self.rc_server.get_status()
        print "Got status from ResourceController:", self.name, self.rc_url
        self.coordinators = {}
        for cinfo in coordinators:
            try: # IF COORDINATOR HAS DIED, STILL WANT TO RETURN RCMonitor...
                self.coordinators[cinfo[0]] = CoordinatorMonitor(cinfo)
            except socket.error, e: # JUST COMPLAIN, BUT CONTINUE...
                print >>sys.stderr, "Unable to connect to coordinator:", \
                        cinfo, e

    def __getattr__(self, attr):
        "just pass on method requests to our rc_server"
        return getattr(self.rc_server, attr)


def test_client(server, **kwargs):
    for id in server:
        print 'ID', id
        yield id
        time.sleep(1)


def test_server():
    return range(1000)

if __name__ == '__main__':
    start_client_or_server(test_client, test_server, [], __file__)

########NEW FILE########
__FILENAME__ = Data

import warnings
warnings.warn('pygr.Data is deprecated.  Use "from pygr import worldbase" \
              instead!', DeprecationWarning, stacklevel=2)

from pygr import worldbase
from metabase import ResourceServer, dumps, OneToManyRelation,\
        OneToOneRelation, ManyToManyRelation, WorldbaseNotPortableError,\
        WorldbaseNotFoundError, WorldbaseMismatchError, WorldbaseEmptyError,\
        WorldbaseReadOnlyError, WorldbaseSchemaError, WorldbaseNoModuleError,\
        ResourceZone

schema = worldbase.schema # ROOT OF OUR SCHEMA NAMESPACE

# PROVIDE TOP-LEVEL NAMES IN OUR RESOURCE HIERARCHY
Bio = worldbase.Bio

getResource = worldbase._mdb # our metabase interface
addResource = worldbase._mdb.add_resource


def addResourceDict(d, layer=None):
    'queue a dict of name:object pairs for saving to specified db layer'
    if layer is not None: # use the named metabase specified by layer
        mdb = worldbase._mdb.zoneDict[layer] # KeyError if layer not found!
    else: # use default MetabaseList
        mdb = worldbase._mdb
    for k, v in d.items(): # queue each resource in the dictionary
        mdb.add_resource(k, v)

addSchema = worldbase._mdb.add_schema
deleteResource = worldbase._mdb.delete_resource
dir = worldbase._mdb.dir


def newServer(*args, **kwargs):
    return ResourceServer(worldbase._mdb, *args, **kwargs)

save = worldbase._mdb.commit
rollback = worldbase._mdb.rollback
list_pending = worldbase._mdb.list_pending
loads = worldbase._mdb.loads
update = worldbase._mdb.update
clear_cache = worldbase._mdb.clear_cache

# TOP-LEVEL NAMES FOR STANDARDIZED LAYERS
here = ResourceZone(getResource, 'here')
my = ResourceZone(getResource, 'my')
system = ResourceZone(getResource, 'system')
subdir = ResourceZone(getResource, 'subdir')
remote = ResourceZone(getResource, 'remote')
MySQL = ResourceZone(getResource, 'MySQL')

__all__ = ('Bio', 'schema', 'getResource', 'addResource', 'addSchema',
           'deleteResource', 'dir', 'newServer', 'save', 'rollback',
           'list_pending', 'loads', 'dumps', 'update', 'clear_cache',
           'OneToManyRelation', 'ManyToManyRelation',
           'OneToOneRelation', 'WorldbaseNotPortableError',
           'WorldbaseNotFoundError', 'WorldbaseMismatchError',
           'WorldbaseEmptyError', 'WorldbaseReadOnlyError',
           'WorldbaseSchemaError', 'WorldbaseNoModuleError',
           'here', 'my', 'system', 'subdir', 'remote', 'MySQL')

########NEW FILE########
__FILENAME__ = dbfile

import anydbm
import shelve
import sys
import UserDict
import logger


class WrongFormatError(IOError):
    'attempted to open db with the wrong format e.g. btree vs. hash'
    pass


class NoSuchFileError(IOError):
    'file does not exist!'
    pass


class PermissionsError(IOError):
    'inadequate permissions for requested file'
    pass


class ReadOnlyError(PermissionsError):
    'attempted to open a file for writing, but no write permission'
    pass


def open_anydbm(*args, **kwargs):
    'trap anydbm.error message and transform to our consistent exception types'
    try:
        return anydbm.open(*args, **kwargs)
    except ImportError, e:
        if str(e).endswith('bsddb') and bsddb:
            # This almost certainly means dbhash tried to import bsddb
            # on a system with only bsddb3 working correctly. In that case,
            # simply do ourselves what anydbm would have done.
            # FIXME: explicitly check if dbhash raised this exception?
            return bsddb.hashopen(*args, **kwargs)
        raise
    except anydbm.error, e:
        msg = str(e)
        if msg.endswith('new db'):
            raise NoSuchFileError(msg)
        elif msg.startswith('db type'):
            raise WrongFormatError(msg)
        raise


try: # detect whether bsddb module available and working...
    import bsddb
    try:
        bsddb.db
    except AttributeError:
        raise ImportError
except ImportError:
    try:    # maybe the external bsddb3 will work instead...
        import bsddb3
        try:
            bsddb3.db
        except AttributeError:
            raise ImportError
        bsddb = bsddb3
    except ImportError: # ...nope
        bsddb = None


def open_bsddb(filename, flag='r', useHash=False, mode=0666):
    """open bsddb index instead of hash by default.
    useHash=True forces it to use anydbm default (i.e. hash) instead.
    Also gives more meaningful error messages."""
    try: # 1ST OPEN AS BTREE
        if useHash: # FORCE IT TO USE HASH INSTEAD OF BTREE
            return open_anydbm(filename, flag)
        else:
            return bsddb.btopen(filename, flag, mode)
    except bsddb.db.DBAccessError: # HMM, BLOCKED BY PERMISSIONS
        if flag=='c' or flag=='w': # TRY OPENING READ-ONLY
            try:
                ifile = file(filename)
            except IOError:
                # Hmm, not even readable. Raise a generic permission error.
                raise PermissionsError('insufficient permissions \
to open file: ' + filename)
            ifile.close()
            # We can read the file, so raise a ReadOnlyError.
            raise ReadOnlyError('file is read-only: '+ filename)
        else: # r OR n FLAG: JUST RAISE EXCEPTION
            raise PermissionsError('insufficient permissions to open file: '
                                   + filename)
    except bsddb.db.DBNoSuchFileError:
        raise NoSuchFileError('no file named: ' + filename)
    except bsddb.db.DBInvalidArgError: # NOT A BTREE FILE...
        try:
            if useHash: # NO POINT IN TRYING HASH YET AGAIN...
                raise bsddb.db.DBInvalidArgError
            # fallback to using default: hash file
            return open_anydbm(filename, flag)
        except bsddb.db.DBInvalidArgError:
            raise WrongFormatError('file does not match expected \
shelve format: ' + filename)


def open_index(filename, flag='r', useHash=False, mode=0666):
    if bsddb is None:
        d = open_anydbm(filename, flag)
        if not useHash:
            logger.warn('Falling back to hash index: unable to import bsddb')
        return d
    return open_bsddb(filename, flag, useHash, mode)


def iter_gdbm(db):
    'iterator for gdbm objects'
    k = db.firstkey()
    while k is not None:
        yield k
        k = db.nextkey(k)


class _ClosedDict(UserDict.DictMixin):
    """This dummy class exists solely to raise a clear error msg if accessed.
    Copied from the Python 2.6 shelve.py """

    def closed(self, *args):
        raise ValueError('invalid operation on closed shelf')
    __getitem__ = __setitem__ = __delitem__ = keys = closed

    def __repr__(self):
        return '<Closed Dictionary>'


class BetterShelf(shelve.Shelf):
    """Shelf subclass that fixes its horrible iter implementation.
    """

    def __iter__(self):
        'avoid using iter provided by shelve/DictMixin, which loads all keys!'
        try:
            return iter(self.dict)
        except TypeError: # gdbm lacks __iter__ method, so try iter_gdbm()
            exc_type, exc_value, exc_traceback = sys.exc_info()
            try:
                self.dict.firstkey
            except AttributeError: # evidently not a gdbm dict
                raise TypeError('''cannot iterate over this dictionary.
This means that you do not have bsddb, bsddb3, or gdbm available for use by
the 'shelve' module in this Python install.  Please fix this!

Original error message was: %s''' % str(exc_value))
            else: # iterate using gdbm-specific method
                return iter_gdbm(self.dict)

    if sys.version_info < (2, 6): # Python finally added good err msg in 2.6

        def close(self):
            if isinstance(self.dict, _ClosedDict):
                return # if already closed, nothing further to do...
            shelve.Shelf.close(self) # close Shelf as usual
            self.dict = _ClosedDict() # raises sensible error msg if accessed


def shelve_open(filename, flag='c', protocol=None, writeback=False,
                useHash=False, mode=0666, *args, **kwargs):
    """improved implementation of shelve.open() that won't generate
bogus __del__ warning messages like Python's version does."""
    d = open_index(filename, flag, useHash, mode) # construct Shelf only if OK
    return BetterShelf(d, protocol, writeback, *args, **kwargs)

########NEW FILE########
__FILENAME__ = downloader
import os
import sys
from classutil import call_subprocess
import logger

# METHODS FOR AUTOMATIC DOWNLOADING OF RESOURCES


def copy_to_file(f, ifile=None, newpath=None, blocksize=8192000):
    'copy from file obj f to ifile (or create newpath if given)'
    if newpath is not None:
        ifile = file(newpath, 'wb') # binary file
    try:
        while True:
            s = f.read(blocksize)
            if s == '':
                break
            ifile.write(s)
    finally:
        if newpath is not None:
            ifile.close()
        f.close()


def do_gunzip(filepath, newpath=None):
    'gunzip the target using Python gzip module'
    from gzip import GzipFile
    if newpath is None:
        newpath = filepath[:-3]
    f = GzipFile(filepath)
    copy_to_file(f, newpath=newpath)
    return newpath


def run_gunzip(filepath, newpath=None):
    'run gunzip program as a sub process'
    if newpath is None:
        newpath = filepath[:-3]
    ifile = open(newpath, 'w+b')
    try:
        if call_subprocess(['gunzip', '-c', filepath], stdout=ifile):
            raise OSError('gunzip "%s" failed!' % filepath)
    finally:
        ifile.close()
    return newpath


def run_unzip(filepath, newpath=None, singleFile=False, **kwargs):
    '''run unzip program as a sub process,
    save to single file newpath if desired.'''
    if newpath is None:
        newpath = filepath[:-4] # DROP THE .zip SUFFIX
    if singleFile: # concatenate all files into newpath
        ifile = file(newpath, 'wb') # copy as binary file
        try:
            status = call_subprocess(['unzip', '-p', filepath], stdout=ifile)
        finally:
            ifile.close()
    else: # just unzip the package as usual
        status = call_subprocess(['unzip', filepath])
    if status != 0:
        raise OSError('unzip "%s" failed!' % filepath)
    return newpath


def create_dir_if_needed(path):
    'ensure that this directory exists, by creating it if needed'
    import os
    if os.path.isdir(path):
        return # directory exists so nothing to do
    create_dir_if_needed(os.path.dirname(path)) # ensure parent exists
    os.mkdir(path) # create this directory


def create_file_with_path(basepath, filepath):
    'create file in write mode, creating parent directory(s) if needed'
    import os.path
    newpath = os.path.join(basepath, filepath)
    create_dir_if_needed(os.path.dirname(newpath))
    return file(newpath, 'wb') # copy as binary file


def do_unzip(filepath, newpath=None, singleFile=False, **kwargs):
    'extract zip archive, to single file given by newpath if desired'
    # WARNING: zipfile module reads entire file into memory!
    if newpath is None:
        newpath = filepath[:-4]
    from zipfile import ZipFile
    t = ZipFile(filepath, 'r')
    try:
        if singleFile: # extract to a single file
            ifile = file(newpath, 'wb') # copy as binary file
            try:
                for name in t.namelist():
                    ifile.write(t.read(name)) # may run out of memory!!
            finally:
                ifile.close()
        else: # extract a bunch of files as usual
            for name in t.namelist():
                ifile = create_file_with_path(newpath, name)
                ifile.write(t.read(name)) # may run out of memory!!
                ifile.close()
    finally:
        t.close()
    return newpath


def do_untar(filepath, mode='r|', newpath=None, singleFile=False, **kwargs):
    'extract tar archive, to single file given by newpath if desired'
    if newpath is None:
        newpath = filepath + '.out'
    import tarfile
    t = tarfile.open(filepath, mode)
    try:
        if singleFile: # extract to a single file
            ifile = file(newpath, 'wb') # copy as binary file
            try:
                for name in t.getnames():
                    f = t.extractfile(name)
                    copy_to_file(f, ifile)
            finally:
                ifile.close()
        else: # extract a bunch of files as usual
            import os
            t.extractall(os.path.dirname(newpath))
    finally:
        t.close()
    return newpath


def uncompress_file(filepath, **kwargs):
    '''stub for applying appropriate uncompression based on file suffix
    (.tar .tar.gz .tgz .tar.bz2 .gz and .zip for now)'''
    if filepath.endswith('.zip'):
        logger.info('unzipping %s...' % filepath)
        try:
            return run_unzip(filepath, **kwargs)
        except OSError:
            return do_unzip(filepath, **kwargs)
    elif filepath.endswith('.tar'):
        logger.info('untarring %s...' % filepath)
        return do_untar(filepath, newpath=filepath[:-4], **kwargs)
    elif filepath.endswith('.tgz'):
        logger.info('untarring %s...' % filepath)
        return do_untar(filepath, mode='r:gz', newpath=filepath[:-4], **kwargs)
    elif filepath.endswith('.tar.gz'):
        logger.info('untarring %s...' % filepath)
        return do_untar(filepath, mode='r:gz', newpath=filepath[:-7], **kwargs)
    elif filepath.endswith('.tar.bz2'):
        logger.info('untarring %s...' % filepath)
        return do_untar(filepath, mode='r:bz2', newpath=filepath[:-8],
                        **kwargs)
    elif filepath.endswith('.gz'):
        logger.info('gunzipping %s...' % filepath)
        try:  # could use gzip module, but it's two times slower!!
            return run_gunzip(filepath, **kwargs) # run as sub process
        except OSError: # on Windows, have to run as python module
            return do_gunzip(filepath, **kwargs)

    return filepath # DEFAULT: NOT COMPRESSED, SO JUST HAND BACK FILENAME


def download_monitor(bcount, bsize, totalsize):
    'show current download progress'
    if bcount == 0:
        download_monitor.percentage_last_shown = 0.
    bytes = bcount * bsize
    percentage = bytes * 100. / totalsize
    if percentage >= 10. + download_monitor.percentage_last_shown:
        logger.info('downloaded %s bytes (%2.1f%%)...'
                    % (bytes, percentage))
        download_monitor.percentage_last_shown = percentage


def download_unpickler(path, filename, kwargs):
    'try to download the desired file, and uncompress it if need be'
    import os
    import urllib
    import classutil
    if filename is None:
        filename = os.path.basename(path)
    try:
        dl_dir = os.environ['WORLDBASEDOWNLOAD']
    except KeyError:
        dl_dir = classutil.get_env_or_cwd('PYGRDATADOWNLOAD')
    filepath = os.path.join(dl_dir, filename)
    logger.info('Beginning download of %s to %s...' % (path, filepath))
    t = urllib.urlretrieve(path, filepath, download_monitor)
    logger.info('Download done.')
    filepath = uncompress_file(filepath, **kwargs) # UNCOMPRESS IF NEEDED
    # PATH TO WHERE THIS FILE IS NOW STORED
    o = classutil.SourceFileName(filepath)
    o._saveLocalBuild = True # MARK THIS FOR SAVING IN LOCAL PYGR.DATA
    return o

download_unpickler.__safe_for_unpickling__ = 1


class SourceURL(object):
    '''unpickling this object will trigger downloading of the desired path,
    which will be cached to WORLDBASEDOWNLOAD directory if any.
    The value returned from unpickling will simply be the path to the
    downloaded file, as a SourceFileName'''
    _worldbase_no_cache = True # force worldbase to always re-load this class

    def __init__(self, path, filename=None, **kwargs):
        self.path = path
        self.kwargs = kwargs
        self.filename = filename
        if path.startswith('http:'): # make sure we can read this URL
            import httplib
            conn = httplib.HTTPConnection(path.split('/')[2])
            try:
                conn.request('GET', '/'.join([''] + path.split('/')[3:]))
                r1 = conn.getresponse()
                if r1.status != 200:
                    raise OSError('http GET failed: %d %s, %s'
                                  % (r1.status, r1.reason, path))
            finally:
                conn.close()

    def __reduce__(self):
        return (download_unpickler, (self.path, self.filename, self.kwargs))


def generic_build_unpickler(cname, args, kwargs):
    'does nothing but construct the specified klass with the specified args'
    if cname == 'BlastDB':
        from seqdb import BlastDB as klass
    else:
        raise ValueError('''class name not registered for unpickling security.
Add it to pygr.downloader.generic_build_unpickler if needed: ''' + cname)
    o = klass(*args, **kwargs)
    o._saveLocalBuild = True # MARK FOR LOCAL PYGR.DATA SAVE
    return o
generic_build_unpickler.__safe_for_unpickling__ = 1


class GenericBuilder(object):
    'proxy for constructing the desired klass on unpickling'
    _worldbase_no_cache = True # force worldbase to always re-load this class

    def __init__(self, cname, *args, **kwargs):
        self.cname = cname
        self.args = args
        self.kwargs = kwargs

    def __reduce__(self):
        return (generic_build_unpickler, (self.cname, self.args, self.kwargs))

########NEW FILE########
__FILENAME__ = graphquery


from __future__ import generators
from mapping import *


class QueryMatchWrapper(dict):
    """build a queryMatch mapping on demand, since its not actually needed
    during query traversal"""

    def __init__(self, dataMatch, compiler):
        dict.__init__(self)
        for k, v in dataMatch.items(): # INVERT THE DATA MATCH MAPPING
            self[v] = k
        for i in range(compiler.n): # ALSO SAVE MAPPINGS TO DATA EDGES
            gqi = compiler.gqi[i]
            self[gqi.fromNode, gqi.queryNode] = compiler.dataEdge[i]


class QueryMatchDescriptor(object):

    def __get__(self, obj, objtype):
        return QueryMatchWrapper(obj.dataMatch, obj)


class QueryMatcher(object):
    "map a query node or edge on demand"

    def __init__(self, compiler):
        self.compiler = compiler

    def __getitem__(self, k):
        for q, d in self.iteritems():
            if q == k:
                return d
        return KeyError

    def __iter__(self, k):
        for k, v in self.iteritems():
            yield k

    def iteritems(self):
        for dataNode, queryNode in self.compiler.dataMatch.items():
            yield queryNode, dataNode # RETURN NODE MAPPINGS
        for i in range(self.compiler.n): # ALSO SAVE MAPPINGS TO DATA EDGES
            gqi = self.compiler.gqi[i] # RETURN EDGE MAPPINGS
            yield (gqi.fromNode, gqi.queryNode), self.compiler.dataEdge[i]

    def items(self):
        return [x for x in self.iteritems()]

    def __repr__(self):
        return '{' + ','.join([repr(k) + ':' + repr(v)
                               for k, v in self.iteritems()]) + '}'


class GraphQueryCompiler(object):
    'compile a series of GraphQueryIterators into python code, run them'
    #queryMatch = QueryMatchDescriptor()
    _lang = "" # NO LANGUAGE STEM

    def __init__(self, name='graphquery', globalDict=None):
        self.name = name
        self.code = []
        self.unmark_code = []
        self.next_code = []
        self.end_code = []
        self.indent = []
        self.gqi = []
        self.queryLayerGraph = dictGraph()
        self.n = 0
        if globalDict is None:
            self._compiled = {}
        else:
            self._compiled = globalDict
        self.queryMatch = QueryMatcher(self)

    def __getitem__(self, key):
        'return appropropriate code for accessing nodes/edges in data or query'
        if key == 'n':
            return self.n
        elif key == 'name':
            return self.name
        elif key == 'dataGraph':
            queryEdge = self.gqi[self.n].queryGraph[self.gqi[self.n].fromNode]\
                    [self.gqi[self.n].queryNode]
            try: # CHECK IF QUERY EDGE USES A NON-DEFAULT DATA GRAPH
                dg = queryEdge['dataGraph']
                return 'self.gqi[%d].dataGraph' % self.n
            except (TypeError, KeyError):
                return 'dataGraph'
        elif key == 'filter':
            return 'self.gqi[%d].filter' % self.n
        elif key == 'toQueryNode':
            return 'self.gqi[%d].queryNode' % self.n
        elif key == 'fromQueryNode':
            return 'self.gqi[%d].fromNode' % self.n
        if key[:2] == 'to':
            layer = self.queryLayerGraph[self.gqi[self.n].queryNode]
        elif key[:4] == 'from':
            layer = self.queryLayerGraph[self.gqi[self.n].fromNode]
        if key[-8:] == 'DataNode': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'dataNode%d' % layer.values()[0]
        if key[-8:] == 'DataEdge': # GET LAST LAYER, WHERE THIS EDGE CREATED
            return 'dataEdge[%d]' % layer.values()[-1]
        if key == 'level':
            return self.n
        try:
            return getattr(self.gqi[self.n], key)
        except AttributeError:
            raise KeyError('%s not a valid GraphQueryCompiler key' % key)

    def indent_code(self, codestr, current_indent):
        'calculate indentation levels added by code in codestr'
        codestr = codestr % self # PERFORM MACRO SUBSTITUTIONS
        lines = codestr.split('\n')
        lastline = lines[-1]
        if lastline == '' and len(lines) > 1: # IGNORE TERMINAL BLANK LINE
            lastline = lines[-2]
        # Determine final indentation level.
        nindent = len(lastline.split('\t')) - 1
        if len(lastline) > 0 and lastline[-1] == ':':
            nindent += 1
        s = '' # NOW FORMAT THE CODE WITH PROPER INDENTATION LEVEL
        for line in lines:
            s += current_indent * '\t' + line + '\n'
        return s, current_indent + nindent

    def __iadd__(self, gqi):
        'add a GraphQueryIterator to be compiled into this query'
        self.gqi.append(gqi)
        if gqi.queryNode not in self.queryLayerGraph: # NOT ALREADY BOUND?
            self.queryLayerGraph += gqi.queryNode
            codestr = getattr(gqi, self._lang + '_generator_code')
            markstr = getattr(gqi, self._lang + '_index_code')
            unmarkstr = getattr(gqi, self._lang + '_unmark_code')
            try:
                endcode = getattr(gqi, self._lang + '_end_code')
            except AttributeError:
                endcode = ''
            try:
                nextcode = getattr(gqi, self._lang + '_next_code')
            except AttributeError:
                nextcode = ''
            self.lastGenerator = self.n
        else:
            codestr = getattr(gqi, self._lang + '_closure_code')
            markstr = None
            unmarkstr = getattr(gqi, self._lang + '_unmark_closure_code')
            try:
                endcode = getattr(gqi, self._lang + '_end_closure_code')
            except AttributeError:
                endcode = ''
            try:
                nextcode = getattr(gqi, self._lang + '_next_closure_code')
            except AttributeError:
                nextcode = ''
        #BIND QUERY EDGE TO THIS LAYER
        self.queryLayerGraph[gqi.queryNode][gqi.fromNode] = self.n
        try: # GET INDENTATION LEVEL FROM PREVIOUS LAYER
            current_indent = self.indent[-1]
        except IndexError:
            current_indent = 1 # TOPLEVEL: MUST INDENT INSIDE def
        self.end_code.append(self.indent_code(endcode, current_indent)[0])
        s, current_indent = self.indent_code(codestr, current_indent)
        self.next_code.append(self.indent_code(nextcode, current_indent)[0])
        if hasattr(gqi, 'filter'):
            s2, current_indent = self.indent_code(getattr(gqi, self._lang + \
                                                          '_filter_code'),
                                                  current_indent)
            s += s2
        if hasattr(gqi, 'filtercode'):
            s2, current_indent = self.indent_code(gqi.filtercode,
                                                  current_indent)
            s += s2
        if markstr is not None:
            s2, current_indent = self.indent_code(markstr, current_indent)
            s += s2
        if unmarkstr is not None:
            s2, tail_indent = self.indent_code(unmarkstr, current_indent)
            self.unmark_code.append(s2)
        else:
            self.unmark_code.append('') # NO UNMARK CODE, SO JUST APPEND BLANK
        self.code.append(s)
        self.indent.append(current_indent)
        self.n += 1
        return self # iadd MUST RETURN self!!
    _def_code = """
def %(name)s(self, dataGraph, dataMatch=None, queryMatch=None):
\tif dataMatch is None: dataMatch={}
\tself.dataMatch = dataMatch
\tdataEdge = %(n)d * [None]
\tself.dataEdge = dataEdge
"""
    _yield_code = 'yield self.queryMatch\n'
    _end_code = ''

    def __str__(self):
        'generate code for this query, as a string function definition'
        s = self._def_code % self
        for layer in self.code: # GENERATE ALL THE TRAVERSAL CODE
            s += layer
        # yield the result
        s2 = self.indent_code(self._yield_code, self.indent[-1])[0]
        s += s2
        i = len(self.unmark_code) - 1
        while i >= 0: # GENERATE THE UNMARKING CODE...
            s += self.unmark_code[i]
            s += self.next_code[i]
            s += self.end_code[i]
            i -= 1
        s += self._end_code % self
        return s

    def run(self, dataGraph, *args, **kwargs):
        'run the query, pre-compiling it if necessary'
        try: # JUST TRY RUNNING OUR FUNCTION: IT RETURNS AN ITERATOR
            return self._compiled[self.name](self, dataGraph, *args, **kwargs)
        except KeyError:
            self.compile()
            # Run it.
            return self._compiled[self.name](self, dataGraph, *args, **kwargs)

    def compile(self):
        'compile using Python exec statement'
        exec str(self) in self._compiled # COMPILE OUR FUNCTION


def find_distutils_lib(path='build'):
    'locate the build/lib path where distutils builds modules'
    import os
    dirs = os.listdir('build')
    for d in dirs:
        if d[:4] == 'lib.':
            return path + '/' + d
    raise OSError((1, 'Unable to locate where distutils built your module!'))


class GraphQueryPyrex(GraphQueryCompiler):
    'compile a series of GraphQueryIterators into pyrex code, run them'
    #queryMatch = QueryMatchDescriptor()
    _lang = "_pyrex" # NO LANGUAGE STEM

    def __getitem__(self, key):
        'return appropropriate code for accessing nodes/edges in data or query'
        if key == 'n':
            return self.n
        elif key == 'name':
            return self.name
        elif key == 'dataGraph':
            try: # CHECK IF QUERY EDGE USES A NON-DEFAULT DATA GRAPH
                queryEdge = self.gqi[self.n].queryGraph[self.gqi[self.n].\
                                          fromNode][self.gqi[self.n].queryNode]
                dg = queryEdge['dataGraph']
                return 'self.gqi[%d].dataGraph' % self.n
            except (TypeError, KeyError):
                return 'dataGraph'
        elif key == 'filter':
            return 'self.gqi[%d].filter' % self.n
        elif key == 'toQueryNode':
            return 'self.gqi[%d].queryNode' % self.n
        elif key == 'fromQueryNode':
            return 'self.gqi[%d].fromNode' % self.n
        if key[:2] == 'to':
            layer = self.queryLayerGraph[self.gqi[self.n].queryNode]
        elif key[:4] == 'from':
            layer = self.queryLayerGraph[self.gqi[self.n].fromNode]
        if key[-8:] == 'DataNode': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'dataNode%d' % layer.values()[0]
        if key[-8:] == 'DataEdge': # GET LAST LAYER, WHERE THIS EDGE CREATED
            return 'dataEdge%d' % layer.values()[-1]
        if key[-8:] == 'DataDict': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'cDict%d' % layer.values()[0]
        if key[-7:] == 'DataPtr': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'pDictEntry%d' % layer.values()[0]
        if key[-11:] == 'DataPtrCont': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'pGraphEntry%d' % layer.values()[0]
        if key[-11:] == 'DataCounter': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'i%d' % layer.values()[0]
        if key == 'toDataNodeUnmatched':
            l = ['dataNode%d!=dataNode%d'
                 % (self.queryLayerGraph[self.gqi[i].queryNode].values()[0],
                  self.queryLayerGraph[self.gqi[self.n].queryNode].values()[0])
               for i in range(self.n)]
            if len(l) > 0:
                return ' and '.join(l)
            else:
                return 'True'
        if key == 'dataNodeDefs':
            return ','.join(['dataNode%d' % i for i in range(self.n)])
        if key == 'dataEdgeDefs':
            return ','.join(['dataEdge%d' % i for i in range(self.n)])
        if key == 'dataDictDefs':
            return ','.join(['*cDict%d' % i for i in range(self.n)])
        if key == 'dataPtrDefs':
            return ','.join(['*pDictEntry%d' % i for i in range(self.n)])
        if key == 'dataPtrContDefs':
            return ','.join(['*pGraphEntry%d' % i for i in range(self.n)])
        if key == 'dataCounterDefs':
            return ','.join(['i%d' % i for i in range(self.n)])
        if key == 'dataCounterArgs':
            return ','.join(['int i%d' % i for i in range(self.n)])
        if key == 'itaVector':
            return ','.join(['ita.vector[%d]' % i for i in range(self.n)])
        if key == 'itaTuple':
            return ',\\\n'.join(['p_ita[%d]' % i for i in range(2 * self.n)])
        if key == 'resultTuple':
            return ',\\\n'.join(['dataNode%d,dataEdge%d'
                 % (self.queryLayerGraph[self.gqi[i].queryNode].values()[0], i)
                                 for i in range(self.n)])
        if key == 'resultTuples':
            return ','.join(['(dataNode%d,dataEdge%d)'
                 % (self.queryLayerGraph[self.gqi[i].queryNode].values()[0], i)
                             for i in range(self.n)])
        if key == 'level' or key == 'nEdges':
            return self.n
        if key == 'lastGenerator':
            return self.lastGenerator
        try:
            return getattr(self.gqi[self.n], key)
        except AttributeError:
            raise KeyError('%s not a valid GraphQueryPyrex key' % key)

    _def_code = """
cimport cdict
cdef c_%(name)s(cdict.CGraphDict cgd, cdict.IntTupleArray ita,
                    %(dataCounterArgs)s):
\tcdef cdict.CGraph *dataGraph
\tcdef cdict.CDict %(dataDictDefs)s
\tcdef cdict.CDictEntry %(dataPtrDefs)s
\tcdef cdict.CDictEntry *pd_temp
\tcdef cdict.CGraphEntry %(dataPtrContDefs)s
\tcdef cdict.CGraphEntry *p_temp
\t#cdef int %(dataCounterDefs)s
\tcdef int %(dataNodeDefs)s
\tcdef int %(dataEdgeDefs)s
\tcdef int *p_ita
\tdataGraph = cgd.d
\tp_ita = ita.data
"""
    _yield_code = """
%(itaTuple)s = %(resultTuple)s
p_ita = p_ita + 2 * %(nEdges)d
ita.n = ita.n + 1
if ita.n >= ita.n_alloc:
\tita.set_vector((%(dataCounterDefs)s), 1)
\treturn
"""
    #results.append((%(resultTuples)s))\n
    _end_code = """
\tita.isDone = 1 # COMPLETED THIS QUERY

from pygr import cdict
def %(name)s(self, g, int maxhit=1000, cdict.IntTupleArray ita=None, qml=None):
\tif not isinstance(g, cdict.CGraphDict):
\t\tg = cdict.CGraphDict(g, cdict.KeyIndex())
\tif ita is None:
\t\tita = cdict.IntTupleArray(maxhit, %(nEdges)d, 2, %(lastGenerator)d)
\tita.n = 0
\tc_%(name)s(g, ita, %(itaVector)s) # RUN THE QUERY
\tif qml is not None:
\t\tqml.matches = ita
\t\treturn qml
\telse:
\t\treturn cdict.QueryMatchList(self, ita, g, %(name)s)
"""

    def compile(self):
        'compile using Pyrex, Distutils, and finally import!'
        import os
        try:
            # We need access to Pygr source code to access cgraph functions
            # in this module.
            pygrpath = os.environ['PYGRPATH']
        except KeyError:
            raise OSError((1,
                           """pyrex compilation requires access to pygr source.
                           Please set the environment variable PYGRPATH to \
                           the top of the pygr source package."""))
        if not os.access(pygrpath + '/pygr/cgraph.c', os.R_OK):
            raise OSError((1, """Unable to access %s/pygr/cgraph.c.
            Is PYGRPATH set to the top of the pygr source package?"""
                           % pygrpath))
        exit_status = os.system('cp %s/pygr/cgraph.c %s/pygr/cgraph.h \
                                %s/pygr/cdict.pxd .'
                                % (pygrpath, pygrpath, pygrpath))
        if exit_status != 0:  # RUN THE PYREX COMPILER TO PRODUCE C
            raise OSError((exit_status,
                           'unable to copy source code to this directory.'))
        # Construct a unique name for the module.
        modulename = self.name + str(id(self))
        myfile = file(modulename + '.pyx', 'w') # GENERATE PYREX CODE
        myfile.write(str(self)) # WRITE CODE
        myfile.close()
        exit_status = os.system('pyrexc %s.pyx' % (modulename))
        if exit_status != 0:  # RUN THE PYREX COMPILER TO PRODUCE C
            raise OSError((exit_status, 'pyrex compilation failed. Is \
pyrexc missing or not in your PATH?'))
        # Build the module using distutils.
        from distutils.core import setup, Extension
        module1 = Extension(modulename, sources=['cgraph.c',
                                                 modulename + '.c'])
        setup(name=modulename,
              description='autogenerated by pygr.graphquery',
              ext_modules=[module1], script_args=['build'])
        # Find out where distutils put our built module.
        modulepath = find_distutils_lib()
        # Work around a nasty problem with Pyrex cimport - there is no way to
        # tell it the module is in a subdirectory! Here, 'from pygr cimport
        # cdict' or 'cimport pygr.cdict' fail; one MUST say 'cimport cdict'.
        import sys
        import os.path
        from pygr import cdict
        # Add the module's location to our path.
        sys.path += [os.path.dirname(cdict.__file__)]
        import imp  # FINALLY, TRY TO IMPORT THE NEW MODULE
        modulefile, path, desc = imp.find_module(modulename, [modulepath])
        # Load and bind the module.
        self._module = imp.load_module(modulename, modulefile, path, desc)
        # Bind our query function.
        self._compiled[self.name] = getattr(self._module, self.name)
        modulefile.close()


class GraphQueryIterator(object):
    """iterator for a single node in graph query.  Subclasses provide different
       flavors of generator methods: graph w/ edges; container; attr;
       function etc."""

    def __init__(self, fromNode, queryNode, dataGraph, queryGraph,
                 dataMatch, queryMatch, attrDict={}):
        self.fromNode = fromNode
        self.queryNode = queryNode
        self.dataGraph = dataGraph
        self.queryGraph = queryGraph
        self.dataMatch = dataMatch
        self.queryMatch = queryMatch
        self.dataNode = None
        for attr, val in attrDict.items():
            # Save our edge information as attributes of this object.
            setattr(self, attr, val)
##         try:
##             self.nq = len(self.queryGraph[self.queryNode])
##         except KeyError:
##             self.nq = 0

    def restart(self):
        "reset the iterator to its beginning"
        self.mustMark = True
        if self.fromNode != None:
            self.dataNode = self.queryMatch[self.fromNode]
        if self.queryNode in self.queryMatch: # ALREADY ASSIGNED TO A DATA NODE
            self.mustMark = False
            if self.fromNode is None: # NO PATH TO HERE, SO JUST ECHO SINGLETON
                self.iterator = self.echo()
            else: # CHECK FOR PATH FROM fromNode TO THIS DATA NODE
                self.iterator = self.closure()
        else:
            self.iterator = self.generate()

    def echo(self):
        "Just return what our node is ALREADY matched to"
        yield self.queryMatch[self.queryNode], None

    def closure(self):
        "This node is already matched. Make sure a path to it (closure) exists"
        targetNode = self.queryMatch[self.queryNode]
        try: # GENERATE IF container HAS EDGE TO targetNode
            container = self.dataGraph[self.dataNode]
            yield targetNode, container[targetNode]
        except KeyError:
            pass

    def generate(self):
        "generate all neighbors of data node matched to fromNode"
        try:
            it = self.dataGraph[self.dataNode]
        except KeyError:
            pass
        else:
            for i, e in it.items():
                yield i, e

    _generator_code = """
try: # GENERATOR
\tit%(level)d = %(dataGraph)s[%(fromDataNode)s]
except KeyError:
\tcontinue
for %(toDataNode)s, %(toDataEdge)s in it%(level)d.items():"""

    _index_code = """
if %(toDataNode)s in dataMatch:
\tcontinue
else:
\tdataMatch[%(toDataNode)s] = %(toQueryNode)s
\t#queryMatch[%(toQueryNode)s] = %(toDataNode)s
\t#queryMatch[%(fromQueryNode)s, %(toQueryNode)s] = %(toDataEdge)s
# THIS LINE PREVENTS COMPILER FROM PUSHING EXTRA INDENTATION LAYER"""

    _filter_code = """
if self.gqi[%(level)d].filter(toNode=%(toDataNode)s, fromNode=%(fromDataNode)s, \
                              edge=%(toDataEdge)s, queryMatch=self.queryMatch, \
                              gqi=self.gqi[%(level)d]):"""

    _unmark_code = """
del dataMatch[%(toDataNode)s]
#del queryMatch[%(toQueryNode)s]
#del queryMatch[%(fromQueryNode)s, %(toQueryNode)s]"""

    _closure_code = """
try: # CLOSURE
\t%(toDataEdge)s = %(dataGraph)s[%(fromDataNode)s][%(toDataNode)s]
except KeyError:
\tpass
else:
\t#queryMatch[%(fromQueryNode)s, %(toQueryNode)s] = %(toDataEdge)s"""

    _unmark_closure_code = """
#del queryMatch[%(fromQueryNode)s, %(toQueryNode)s]"""

    # PYREX CODE
    _pyrex_generator_code = """
p_temp = cdict.cgraph_getitem(%(dataGraph)s, %(fromDataNode)s)
if p_temp != NULL:
\t%(fromDataDict)s = p_temp[0].v
\t%(toDataPtr)s = %(fromDataDict)s[0].dict
\twhile %(toDataCounter)s < %(fromDataDict)s[0].n:
\t\t%(toDataNode)s = %(toDataPtr)s[%(toDataCounter)s].k
\t\t%(toDataEdge)s = %(toDataPtr)s[%(toDataCounter)s].v
"""
    #for %(toDataCounter)s from 0 <= %(toDataCounter)s < %(fromDataDict)s[0].n:

    _pyrex_index_code = 'if %(toDataNodeUnmatched)s:'

    _pyrex_unmark_code = '# COMPILER NEEDS AT LEAST ONE LINE, \
                          EVEN THOUGH NOTHING TO DO HERE'

    _pyrex_next_code = '%(toDataCounter)s = %(toDataCounter)s + 1'

    _pyrex_end_code = '%(toDataCounter)s = 0'

    _pyrex_closure_code = """
p_temp = cdict.cgraph_getitem(%(dataGraph)s, %(fromDataNode)s)
if p_temp != NULL:
\t%(fromDataDict)s = p_temp[0].v
\tpd_temp = cdict.cdict_getitem(%(fromDataDict)s, %(toDataNode)s)
\tif pd_temp != NULL:
\t\t%(toDataEdge)s = pd_temp[0].v
"""

    _pyrex_unmark_closure_code = '# COMPILER NEEDS AT LEAST ONE LINE, \
                                  EVEN THOUGH NOTHING TO DO HERE'

    def unmark(self):
        "erase node and edge assignment associated with the iterator"
        if self.mustMark and self.queryNode in self.queryMatch:
            i = self.queryMatch[self.queryNode] # ERASE OLD NODE ASSIGNMENT
            del self.dataMatch[i]
            del self.queryMatch[self.queryNode]
        try:
            # Erase old edge.
            del self.queryMatch[(self.fromNode, self.queryNode)]
        except KeyError:
            pass

    def next(self):
        "returns the next node from iterator that passes all tests"
        self.unmark()
        for i, e in self.iterator: # RETURN THE FIRST ACCEPTABLE ITEM
##             try:
##                 # Check the number of outgoing edges. NOTE: This check
##                 # will NOT work if multiple graphs are queried!
##                 nd = len(self.dataGraph[i])
##             except KeyError:
##                 nd = 0
##             if nd >= self.nq and
            if self.mustMark and i in self.dataMatch:
                continue # THIS NODE ALREADY ASSIGNED. CAN'T REUSE IT!
            if (not hasattr(self, 'filter') # APPLY EDGE / NODE TESTS HERE
               or self.filter(toNode=i, fromNode=self.dataNode, edge=e,
                               queryMatch=self.queryMatch, gqi=self)):
                if self.mustMark:
                    # Save this node assignment.
                    self.dataMatch[i] = self.queryNode
                    self.queryMatch[self.queryNode] = i
                if e is not None: # SAVE EDGE INFO, IF ANY
                    self.queryMatch[(self.fromNode, self.queryNode)] = e
                return i  # THIS ITEM PASSES ALL TESTS.  RETURN IT
        return None # NO MORE ITEMS FROM THE ITERATOR


class ContainerGQI(GraphQueryIterator):
    "Iterate over all nodes in self.dataGraph"

    def generate(self):
        for i in self.dataGraph:
            yield i, None

    _generator_code = """
%(toDataEdge)s = None # CONTAINER
for %(toDataNode)s in dataGraph:"""

    _pyrex_generator_code="""
%(toDataPtrCont)s = %(dataGraph)s[0].dict
for %(toDataCounter)s from 0 <= %(toDataCounter)s < %(dataGraph)s[0].n:
\t%(toDataNode)s = %(toDataPtrCont)s[%(toDataCounter)s].k
\t%(toDataEdge)s = -1 # NO EDGE INFO
"""


class AttributeGQI(GraphQueryIterator):
    "Iterate over all nodes in attribute called self.attr of self.dataNode"

    def generate(self):
        for i, e in getattr(self.dataNode, self.attr).items():
            yield i, e

    _generator_code = """
for %(toDataNode)s, %(toDataEdge)s in getattr(%(fromDataNode)s, \
                                              '%(attr)s').items():"""


class AttrContainerGQI(GraphQueryIterator):
    """Iterate over all nodes in attribute called self.attrN of self.dataNode
    (no edge info)"""

    def generate(self):
        for i in getattr(self.dataNode, self.attrN):
            yield i, None

    _generator_code = """
%(toDataEdge)s = None
for %(toDataNode)s in getattr(%(fromDataNode)s, '%(attrN)s'):"""


class CallableGQI(GraphQueryIterator):
    "Call the specified function self.f as iterator"

    def generate(self):
        for i, e in self.f(self.dataNode, self.dataGraph, self):
            yield i, e

    _generator_code = """
for %(toDataNode)s, %(toDataEdge)s in self.gqi[%(level)d].f(%(fromDataNode)s, \
                                            dataGraph, self.gqi[%(level)d]):"""


class CallableContainerGQI(GraphQueryIterator):
    "Call the specified function self.fN as iterator (no edge info)"

    def generate(self):
        for i in self.fN(self.dataNode, self.dataGraph, self):
            yield i, None

    _generator_code = """
%(toDataEdge)s = None
for %(toDataNode)s in self.gqi[%(level)d].fN(%(fromDataNode)s, dataGraph, \
                                             self.gqi[%(level)d]):"""


class SubqueryGQI(GraphQueryIterator):
    """base class for running subqueries; produces a union of all subquery
    solutions. self.subqueries must be list of graph objects, each
    representing a subquery"""

    def __init__(self, fromNode, queryNode, dataGraph, queryGraph,
                 dataMatch, queryMatch, attrDict={}):
        GraphQueryIterator.__init__(self, fromNode, queryNode, dataGraph,
                                    queryGraph, dataMatch, queryMatch,
                                    attrDict)
        self.graphQueries = []
        for qg in self.subqueries: # INITIALIZE OUR SUBQUERIES
            self.graphQueries.append(self.gqClass(self.dataGraph, qg,
                                                  dataMatch, queryMatch))

    def closure(self):
        "Generate union of all solutions returned by all subqueries"
        for gq in self.graphQueries:
            for d in gq: # LAUNCHES THE GRAPH QUERY, GETS ALL ITS SOLUTIONS
                yield self.queryMatch[self.queryNode], None
            # Remove its query-data mapping before going to the next subquery.
            gq.cleanup()


def newGQI(self, oclass, fromNode, toNode, dataGraph, queryGraph,
           dataMatch, queryMatch, gqiDict):
    """figure out a default GQI class to use, based on an attribute dictionary,
       then return a new object of that class initialized with the input data
       """
    if fromNode is not None and toNode is not None and \
           queryGraph[fromNode][toNode] is not None:
        kwargs = queryGraph[fromNode][toNode]
        for attr in kwargs:
            try:
                # Use attribute name to determine default class.
                oclass = gqiDict[attr]
            except KeyError:
                pass
    else:
        kwargs = {}
    try:
        oclass = kwargs['__class__'] # LET USER SET CLASS TO USE
    except KeyError:
        pass
    return oclass(fromNode, toNode, dataGraph, queryGraph, dataMatch,
                  queryMatch, kwargs)


class GraphQuery(object):
    "represents a single query or subquery"
    # DEFAULT MAPPING OF ATTRIBUTE NAMES TO GQI CLASSES TO USE WITH THEM
    gqiDict = {'attr': AttributeGQI,
               'attrN': AttrContainerGQI,
               'f': CallableGQI,
               'fN': CallableContainerGQI,
               'subqueries': SubqueryGQI}
    newGQI = newGQI # USE THIS METHOD TO CHOOSE GQI CLASS FOR EACH ITERATOR

    def __init__(self, dataGraph, queryGraph, dataMatch=None, queryMatch=None):
        """Enumerate nodes in queryGraph in BFS order,
        constructing iterator stack"""
        self.dataGraph = dataGraph
        self.queryGraph = queryGraph
        if dataMatch is None:
            dataMatch = {}
        if queryMatch is None:
            queryMatch = {}
        self.dataMatch = dataMatch
        self.queryMatch = queryMatch
        # First we need to find start nodes: process them first and mark them
        # as generate all.
        isFollower = {}
        for node in queryGraph:
            for node2 in queryGraph[node]:
                # node2 has an incoming edge so it cannot be a start node.
                isFollower[node2] = True
        q = []
        self.q = q
        n = 0
        for node in queryGraph: # PLACE START NODES AT HEAD OF QUEUE
            if node not in isFollower:
                q.append(self.newGQI(ContainerGQI, None, node, dataGraph,
                                     queryGraph, dataMatch, queryMatch,
                                     self.gqiDict))
                n += 1
        if n == 0:
            # No start nodes; just add the first query node to the queue.
            for node in queryGraph:
                q.append(self.newGQI(ContainerGQI, None, node, dataGraph,
                                     queryGraph, dataMatch, queryMatch,
                                     self.gqiDict))
                n += 1
                break # Only add the first node.
        if n == 0:
            raise ValueError('query graph is empty!')

        visited = {}
        i = 0
        while i < n:
            # Add node to the queue even if it's already been visited
            # - but don't add its neighbours.
            if q[i].queryNode not in visited: # ADD NEIGHBORS TO THE QUEUE
                visited[q[i].queryNode] = True # MARK AS VISITED
                for node in queryGraph[q[i].queryNode]: # GET ALL ITS NEIGHBORS
                    #print 'QUEUE:', n, node
                    q.append(self.newGQI(GraphQueryIterator, q[i].queryNode,
                                         node, dataGraph, queryGraph,
                                         dataMatch, queryMatch,
                                         self.gqiDict))
                    n += 1
            i += 1

    def __iter__(self):
        "generates all subgraphs of dataGraph matching queryGraph"
        i = 0
        n = len(self.q)
        self.q[0].restart() # PRELOAD ITERATOR FOR 1ST NODE
        while i >= 0:
            dataNode = self.q[i].next()
            if dataNode is not None:
                #print i,qu[i].queryNode,dataNode
                if i + 1 < n: # MORE LEVELS TO QUERY?
                    i += 1 # ADVANCE TO NEXT QUERY LEVEL
                    self.q[i].restart()
                else:  # GRAPH MATCH IS COMPLETE!
                    yield self.queryMatch # RETURN COMPLETE MATCH

            else: # NO MORE ACCEPTABLE NODES AT THIS LEVEL, SO BACKTRACK
                i -= 1

    def cleanup(self):
        "erase any query:data node matching associated with this subquery"
        for q in self.q:
            q.unmark()

    def compile(self, globals=None, compilerClass=GraphQueryCompiler,
                **kwargs):
        """return a compiled version of this query, using globals namespace
        if specified"""
        compiler = compilerClass(globalDict=globals, **kwargs)
        for gqi in self.q:
            compiler += gqi
        return compiler


SubqueryGQI.gqClass = GraphQuery # CLASS FOR CONSTRUCTING SUBQUERIES

########NEW FILE########
__FILENAME__ = logger
"""
Implements logging functionality

Upon import creates a module level log class (log) and
the following logging functions:

debug, info, warn and error

The default formatters will print out the function the log was triggered from.
"""

import logging
import sys

# python 2.5 the watershed release that introduced most changes since 2.1

PYTHON_25 = sys.version_info >= (2, 5)


def get_logger(name='pygr-log', stream=sys.stdout, formatter=None):
    """
    Returns a logger

    >>> disable('INFO')
    >>> info('logtest, this message SHOULD NOT be visible')
    >>> disable()
    >>> info('logtest, this message should be visible')
    >>> disable('DEBUG')
    >>> debug('logtest, this message SHOULD NOT be visible')
    >>> info('logtest, this message should be visible')
    """
    logger = logging.getLogger(name)

    # this is needed in case the process is
    # forked/multithreaded; loggers exist in a global scope
    # we don't want each import to duplocate this handler

    if not logger.handlers:
        console = logging.StreamHandler(stream)
        console.setLevel(logging.DEBUG)
        if PYTHON_25:
            format = '%(levelname)s %(module)s.%(funcName)s: %(message)s'
        else:
            format = '%(levelname)s %(module)s: %(message)s'

        formatter = formatter or logging.Formatter(format)
        console.setFormatter(formatter)
        logger.addHandler(console)
        logger.setLevel(logging.DEBUG)
    return logger


def disable(level=0):
    """
    Disables logging levels
    Levels: DEBUG, INFO, WARNING, ERROR

    >>> disable('INFO')
    >>> info('logtest, this message SHOULD NOT be visible')
    """
    level = str(level)
    value = dict(NOTSET=0, DEBUG=10, INFO=20, WARNING=30, ERROR=40)\
            .get(level.upper(), 0)
    logging.disable(value)


# populate some loggers by default
log = get_logger()
debug, info, warn, error = log.debug, log.info, log.warn, log.error


def test(verbose=0):
    "Performs module level testing"
    import doctest
    doctest.testmod(verbose=verbose)


if __name__ == "__main__":
    test()

########NEW FILE########
__FILENAME__ = mapping


from __future__ import generators
from schema import *
import classutil


def update_graph(self, graph):
    'save nodes and edges of graph to self'
    for node, d in graph.iteritems():
        self += node
        saveDict = self[node]
        for target, edge in d.iteritems():
            saveDict[target] = edge


class PathList(list):
    """Internal representation for storing both nodes and edges as list
    So filter functions can see both nodes and edges"""

    def __init__(self, nodes=None, edges=None):
        if nodes != None:
            list.__init__(self, nodes)
        else:
            list.__init__(self)
        if edges != None:
            self.edge = list(edges)
        else:
            self.edge = []

    def append(self, val):
        list.append(self, val)
        self.edge.append(val)

    def extend(self, l):
        list.extend(self, l) # EXTEND TOP-LEVEL LIST AS USUAL
        try: # EXTEND OUR EDGE LIST AS WELL
            self.edge.extend(l.edge)
        except AttributeError: #IF l HAS NO EDGES, PAD OUR EDGE LIST WITH Nones
            self.edge.extend(len(l) * [None])


class Edge(list):
    "Interface to edge information."
    isDirected = False

    def __init__(self, graph, nodes, edgeInfo):
        self.graph = graph
        if edgeInfo:
            self.edgeInfo = edgeInfo
        list.__init__(self, nodes) # SAVE NODES AS TUPLE

    def __getattr__(self, attr):
        try:
            return getattr(self.edgeInfo, attr)
        except AttributeError:
            if isinstance(self.edgeInfo, types.DictType):
                # Treat edgeInfo as an attribute dictionary.
                return self.edgeInfo[attr]
            raise AttributeError(attr)

    # Should we define setattr here too, to allow users to add new attribute
    # values? The problem is setattr is painful to implement due to the
    # recursive reference problem.

    def __cmp__(self, other): # DO WE NEED TO COMPARE EDGE INFO??
        if not isinstance(other, Edge): # CAN ONLY COMPARE A PAIR OF EDGES
            return -1
        diff = cmp(self.graph, other.graph)
        if diff: # NOT IN THE SAME GRAPH...
            return diff
        elif self.isDirected: # IF DIRECTED, JUST COMPARE IN CURRENT ORDER
            return tuple.__cmp__(self, other)
        else: # UNDIRECTED COMPARISON REQUIRES PUTTING BOTH IN SAME ORDER
            me = [i for i in self]
            you = [i for i in other]
            me.sort()
            you.sort()
            return cmp(me, you)

    # NEEDS SCHEMA SUPPORT: RETURN A SINGLE SCHEMA TUPLE DESCRIBING THIS EDGE.

class DirectedEdge(Edge):
    isDirected = True


# need a class to provide access to the edges in a graph
# iterator, membership test
#class EdgeSet


class dictEdge(dict):
    """2nd layer graph interface implemenation using dict.
    """
    dictClass = dict

    def __init__(self, graph, fromNode):
        self.graph = graph
        self.fromNode = fromNode
        self.dictClass.__init__(self) # INITIALIZE TOPLEVEL DICTIONARY

    def __iadd__(self, target):
        "Add edge from fromNode to target with no edge-info"
        self[target] = None
        return self # THIS IS REQUIRED FROM iadd()!!

    def __setitem__(self, target, edgeInfo):
        "Add edge from fromNode to target with edgeInfo"
        self.dictClass.__setitem__(self, target, edgeInfo)
        if target not in self.graph: # ADD NEW NODE TO THE NODE DICT
            self.graph += target

    _setitem_ = dict.__setitem__ # INTERNAL INTERFACE FOR SAVING AN ENTRY

    def __delitem__(self, target):
        "Delete edge from fromNode to target"
        try:
            self.dictClass.__delitem__(self, target)
        except KeyError: # GENERATE A MORE INFORMATIVE ERROR MESSAGE
            raise KeyError('No edge from node to target')

    def __isub__(self, target):
        "Delete edge from fromNode to target"
        self.__delitem__(target)
        return self # THIS IS REQUIRED FROM iadd()!!

    def edges(self):
        "Return iterator for accessing edges from fromNode"
        for target, edgeInfo in self.items():
            if isinstance(edgeInfo, Edge):
                yield edgeInfo
            else:
                yield Edge(self.graph, (self.fromNode, target, edgeInfo),
                           edgeInfo)


class dictGraph(dict):
    """Top layer graph interface implemenation using dict.
    """
    dictClass = dict
    edgeDictClass = dictEdge

    def __init__(self, schema=None, domain=None, range=None):
        if schema and domain and range:
            if domain not in schema:
                schema += domain #ADD DOMAIN AS NODE TO schema GRAPH
            schema[domain][range] = self
        self.dictClass.__init__(self) # INITIALIZE TOPLEVEL DICTIONARY

    def __iadd__(self, node, ruleSet=False):
        "Add node to graph with no edges"
        if node not in self:
            self.dictClass.__setitem__(self, node, self.edgeDictClass(self,
                                                                      node))
            if ruleSet == False:
                ruleSet = getschema(node, graph=self)
            for rule in ruleSet:
                if isinstance(rule[1], types.StringType):
                    # Attribute binding; bind directly to attribute.
                    setattr(node, rule[1], self[node])
        return self # THIS IS REQUIRED FROM iadd()!!

    def __setitem__(self, node, target):
        "This method exists only to support g[n]+=o.  Do not use as g[n]=foo."
        if self[node] != target:
            raise ValueError('Incorrect usage. Add edges using g[n]+=o \
                             or g[n][o]=edge.')

    def __delitem__(self, node):
        "Delete node from graph."
        # Grr, we really need to find all edges going to this node
        # and delete them.
        try:
            # Do stuff to remove it here...
            self.dictClass.__delitem__(self, node)
        except KeyError:
            raise KeyError('Node not present in mapping.')
        for rule in getschema(node, graph=self):
            if isinstance(rule[1], types.StringType): # ATTRIBUTE BINDING!
                delattr(node, rule[1])  # REMOVE ATTRIBUTE BINDING

    def __isub__(self, node):
        "Delete node from graph"
        self.__delitem__(node)
        return self # THIS IS REQUIRED FROM isub()!!

    def __hash__(self): # SO SCHEMA CAN INDEX ON GRAPHS...
        return id(self)

    def edges(self):
        "Return iterator for all edges in this graph"
        for edgedict in self.values():
            for edge in edgedict.edges():
                yield edge
    update = update_graph


class dictEdgeFB(dictEdge):
    "dictEdge subclass that saves both forward and backward edges"

    def __setitem__(self, target, edgeInfo):
        "Save edge in both forward and backward dicts."
        dictEdge.__setitem__(self, target, edgeInfo) # FORWARD EDGE
        try:
            d = self.graph._inverse[target]
        except KeyError:
            d = self.dictClass()
            self.graph._inverse[target] = d
        d[self.fromNode] = edgeInfo # SAVE BACKWARD EDGE

    def __invert__(self):
        "Get nodes with edges to this node"
        return self.graph._inverse[self.fromNode]


class dictGraphFB(dictGraph):
    "Graph that saves both forward and backward edges"

    def __init__(self, **kwargs):
        dictGraph.__init__(self, **kwargs)
        self._inverse = self.dictClass()
    __invert__ = classutil.standard_invert

    def __delitem__(self, node):
        "Delete node from the graph"
        try:
            fromNodes = self._inverse[node]
            del self._inverse[node] # REMOVE FROM _inverse DICT
        except KeyError:
            pass
        else: # DELETE EDGES TO THIS NODE
            for i in fromNodes:
                del self[i][node]
        dictGraph.__delitem__(self, node)


def listUnion(ivals):
    'merge all items using union operator'
    union = None
    for ival in ivals:
        try:
            union += ival
        except TypeError:
            union = ival
    return union


class DictQueue(dict):
    'each index entry acts like a queue; setitem PUSHES, and delitem POPS'

    def __setitem__(self, k, val):
        try:
            dict.__getitem__(self, k).append(val)
        except KeyError:
            dict.__setitem__(self, k, [val])

    def __getitem__(self, k):
        return dict.__getitem__(self, k)[0]

    def __delitem__(self, k):
        l=dict.__getitem__(self, k)
        del l[0]
        if len(l) == 0:
            dict.__delitem__(self, k)


################################ PYGR.DATA.SCHEMA - AWARE CLASSES BELOW


def close_if_possible(self):
    'close storage to ensure any pending data is written'
    try:
        do_close = self.d.close
    except AttributeError:
        pass
    else:
        do_close()


class Collection(object):
    'flexible storage mapping ID --> OBJECT'

    def __init__(self, saveDict=None, dictClass=dict, **kwargs):
        '''saveDict, if not None, the internal mapping to use as our storage.
        filename: if provided, a file path to a shelve (BerkeleyDB) file to
              store the data in.
        dictClass: if provided, the class to use for storage of dict data.'''
        if saveDict is not None:
            self.d = saveDict
        elif 'filename' in kwargs: # USE A SHELVE (BERKELEY DB)
            try:
                if kwargs['intKeys']: # ALLOW INT KEYS, HAVE TO USE IntShelve
                    self.__class__ = IntShelve
                else:
                    raise KeyError
            except KeyError:
                self.__class__ = PicklableShelve
            return self.__init__(**kwargs)
        else:
            self.d = dictClass()
        classutil.apply_itemclass(self, kwargs)

    def __getitem__(self, k):
        return self.d[k]

    def __setitem__(self, k, v):
        self.d[k] = v

    def __delitem__(self, k):
        del self.d[k]

    def __len__(self):
        return len(self.d)

    def __contains__(self, k):
        return k in self.d

    def __iter__(self):
        return iter(self.d)

    def __getattr__(self, attr):
        if attr == '__setstate__' or attr == '__dict__':
            # This prevents infinite recursion during unpickling.
            raise AttributeError
        try: # PROTECT AGAINST INFINITE RECURSE IF NOT FULLY __init__ED...
            return getattr(self.__dict__['d'], attr)
        except KeyError:
            raise AttributeError('Collection has no subdictionary')
    close = close_if_possible

    def __del__(self):
        'must ensure that shelve object is closed to save pending data'
        try:
            self.close()
        except classutil.FileAlreadyClosedError:
            pass


class PicklableShelve(Collection):
    'persistent storage mapping ID --> OBJECT'

    def __init__(self, filename, mode=None, writeback=False,
                 unpicklingMode=False, verbose=True, **kwargs):
        '''Wrapper for a shelve object that can be pickled.  Ideally, you
should specify a TWO letter mode string: the first letter to
indicate what mode the shelve should be initially opened in, and
the second to indicate the mode to open the shelve during unpickling.
e.g. mode='nr': to create an empty shelve (writable),
which in future will be re-opened read-only.
Also, mode=None makes it first attempt to open read-only, but if the file
does not exist will create it using mode 'c'. '''
        # Mark this string as a file path.
        self.filename = classutil.SourceFileName(str(filename))
        self.writeback = writeback
        if unpicklingMode or mode is None or mode == 'r':
            # Just use mode as given.
            self.mode = mode
        elif mode == 'n' or mode == 'c' or mode == 'w':
            # Ambiguous modes, warn & set default.
            if verbose:
                import sys
                print >>sys.stderr, '''Warning: you opened shelve file %s
in mode '%s' but this is ambiguous for how the shelve should be
re-opened later during unpickling.  By default it will be
re-opened in mode 'r' (read-only).  To make it be re-opened
writable, create it in mode '%sw', or call its method
reopen('w'), which will make it be re-opened in mode 'w' now and
in later unpickling.  To suppress this warning message, use the
verbose=False option.''' % (filename, mode, mode)
            self.mode = 'r'
        else: # PROCESS UNAMBIGUOUS TWO-LETTER mode STRING
            try:
                if len(mode) == 2 and mode[0] in 'ncwr' and mode[1] in 'cwr':
                    self.mode = mode[1] # IN FUTURE OPEN IN THIS MODE
                    mode = mode[0] # OPEN NOW IN THIS MODE
                else:
                    raise ValueError('invalid mode string: ' + mode)
            except TypeError:
                raise ValueError('file mode must be a string!')
        if unpicklingMode:
            self.d = classutil.open_shelve(filename, mode, writeback,
                                           allowReadOnly=True)
        else:
            self.d = classutil.open_shelve(filename, mode, writeback)
        classutil.apply_itemclass(self, kwargs)

    __getstate__ = classutil.standard_getstate ############### PICKLING METHODS
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(filename=0, mode=0, writeback=0)

    def close(self):
        '''close our shelve index file.'''
        self.d.close()

    def __setitem__(self, k, v):
        try:
            self.d[k] = v
        except TypeError:
            raise TypeError('to allow int keys, you must pass intKeys=True \
to constructor!')

    def reopen(self, mode='r'):
        're-open shelve in the specified mode, and save mode on self'
        self.close()
        self.d = classutil.open_shelve(self.filename, mode,
                                       writeback=self.writeback)
        self.mode = mode


class IntShelve(PicklableShelve):
    'provides an interface to shelve that can use int as key'

    def saveKey(self, i):
        'convert to string key'
        if isinstance(i, int):
            return 'int:%s' % i
        elif isinstance(i, str):
            return i
        try:
            return 'int:%s' % int(i)
        except TypeError:
            pass
        raise KeyError('IntShelve can only save int or str as key')

    def trueKey(self, k):
        "convert back to key's original format"
        if k.startswith('int:'):
            return int(k[4:])
        else:
            return k

    def __getitem__(self, k):
        return self.d[self.saveKey(k)]

    def __setitem__(self, k, v):
        self.d[self.saveKey(k)] = v

    def __delitem__(self, k):
        del self.d[self.saveKey(k)]

    def __contains__(self, k):
        return self.saveKey(k) in self.d

    def __iter__(self): ################ STANDARD ITERATOR METHODS
        for k in self.d:
            yield self.trueKey(k)

    def keys(self):
        return [k for k in self]

    def iteritems(self):
        for k, v in self.d.iteritems():
            yield self.trueKey(k), v

    def items(self):
        return [k for k in self.iteritems()]


## PACKING / UNPACKING METHODS FOR SEPARATING INTERNAL VS. EXTERNAL
## REPRESENTATIONS OF GRAPH NODES AND EDGES
## 1. ID-BASED PACKING: USE obj.id AS INTERNAL REPRESENTATION
##
## 2. TRIVIAL: INTERNAL AND EXTERNAL REPRESENTATIONS IDENTICAL
##    WORKS WELL FOR STRING OR INT NODES / EDGES.
##
## 3. PICKLE PACKING: USE PICKLE AS INTERNAL REPRESENTATION
def pack_id(self, obj):
    'extract id attribute from obj'
    try:
        return obj.id
    except AttributeError:
        if obj is None:
            return None
        raise


def unpack_source(self, objID):
    return self.sourceDB[objID]


def unpack_target(self, objID):
    return self.targetDB[objID]


def unpack_edge(self, objID):
    try:
        return self.edgeDB[objID]
    except KeyError:
        if objID is None:
            return None
        raise


def add_standard_packing_methods(localDict):
    localDict['pack_source'] = pack_id
    localDict['pack_target'] = pack_id
    localDict['pack_edge'] = pack_id
    localDict['unpack_source'] = unpack_source
    localDict['unpack_target'] = unpack_target
    localDict['unpack_edge'] = unpack_edge


def add_trivial_packing_methods(localDict):
    for name in ('pack_source', 'pack_target', 'pack_edge',
                 'unpack_source', 'unpack_target', 'unpack_edge'):
        localDict[name] = lambda self, obj: obj


def pack_pickle(self, obj):
    'get pickle string for obj'
    import pickle
    return pickle.dumps(obj)


def unpack_pickle(self, s):
    'unpickle string to get obj'
    import pickle
    return pickle.loads(s)


class MappingInverse(object):

    def __init__(self, db):
        self._inverse = db
        self.attr = db.inverseAttr

    def __getitem__(self, k):
        return self._inverse.sourceDB[getattr(k, self.attr)]
    __invert__ = classutil.standard_invert


class Mapping(object):
    '''dict-like class suitable for persistent usages.  Extracts ID values from
    keys and values passed to it, and saves IDs into its internal dictionary
    instead of the actual objects.  Thus, the external interface is objects,
    but the internal storage is ID values.'''

    def __init__(self, sourceDB, targetDB, saveDict=None, IDAttr='id',
                 targetIDAttr='id', itemAttr=None, multiValue=False,
                 inverseAttr=None, **kwargs):
        '''sourceDB: dictionary that maps key ID values to key objects
        targetDB: dictionary that maps value IDs to value objects
        saveDict, if not None, is the internal mapping to use as our storage
        IDAttr: attribute name to obtain an ID from a key object
        targetIDAttr: attribute name to obtain an ID from a value object
        itemAttr, if not None, the attribute to obtain target (value) ID
           from an internal storage value
        multiValue: if True, treat each value as a list of values.
        filename: if provided, is a file path to a shelve (BerkeleyDB) file to
              store the data in.
        dictClass: if not None, is the class to use for storage of dict data'''
        if saveDict is None:
            self.d = classutil.get_shelve_or_dict(**kwargs)
        else:
            self.d = saveDict
        self.IDAttr = IDAttr
        self.targetIDAttr = targetIDAttr
        self.itemAttr = itemAttr
        self.multiValue = multiValue
        self.sourceDB = sourceDB
        self.targetDB = targetDB
        if inverseAttr is not None:
            self.inverseAttr = inverseAttr

    def __getitem__(self, k):
        kID = getattr(k, self.IDAttr)
        return self.getTarget(self.d[kID])

    def getTarget(self, vID):
        if self.itemAttr is not None:
            vID = getattr(vID, self.itemAttr)
        if self.multiValue:
            return [self.targetDB[j] for j in vID]
        else:
            return self.targetDB[vID]

    def __setitem__(self, k, v):
        if self.multiValue:
            v = [getattr(x, self.targetIDAttr) for x in v]
        else:
            v = getattr(v, self.targetIDAttr)
        self.d[getattr(k, self.IDAttr)] = v

    def __delitem__(self, k):
        del self.d[getattr(k, self.IDAttr)]

    def __contains__(self, k):
        return getattr(k, self.IDAttr) in self.d

    def __len__(self):
        return len(self.d)

    def clear(self):
        self.d.clear()

    def copy(self):
        return Mapping(self.sourceDB, self.targetDB, self.d.copy(),
                       self.IDAttr, self.targetIDAttr, self.itemAttr,
                       self.multiValue)

    def update(self, b):
        for k, v in b.iteritems():
            self[k] = v

    def get(self, k, v=None):
        try:
            return self[k]
        except KeyError:
            return v

    def setdefault(self, k, v=None):
        try:
            return self[k]
        except KeyError:
            self[k] = v
            return v

    def pop(self, k, v=None):
        try:
            v = self[k]
        except KeyError:
            return v
        del self[k]
        return v

    def popitem(self):
        kID, vID = self.d.popitem()
        return kID, self.getTarget(vID)

    def __iter__(self): ######################## ITERATORS
        for kID in self.d:
            yield self.sourceDB[kID]

    def keys(self):
        return [k for k in self]

    def itervalues(self):
        for vID in self.d.itervalues():
            yield self.getTarget(vID)

    def values(self):
        return [v for v in self.itervalues()]

    def iteritems(self):
        for kID, vID in self.d.iteritems():
            yield self.sourceDB[kID], self.getTarget(vID)

    def items(self):
        return [x for x in self.iteritems()]

    __invert__ = classutil.standard_invert
    _inverseClass = MappingInverse
    close = close_if_possible

    def __del__(self):
        close_if_possible(self)


def graph_cmp(self, other):
    'compare two graph dictionaries'
    import sys
    diff = cmp(len(self), len(other))
    if diff != 0:
        print >>sys.stderr, 'len diff:', len(self), len(other)
        return diff
    for node, d in self.iteritems():
        try:
            d2 = other[node]
        except KeyError:
            print >>sys.stderr, 'other missing key'
            return 1
        diff = cmp(d, d2)
        if diff != 0:
            print >>sys.stderr, 'value diff', d, d2
            return diff
    return 0


class IDNodeDict(object):
    """2nd layer graph interface implementation using proxy dict.
       e.g. shelve."""
    dictClass = dict

    def __init__(self, graph, fromNode):
        self.graph = graph
        self.fromNode = fromNode

    def __getitem__(self, target): ############# ACCESS METHODS
        edgeID = self.graph.d[self.fromNode][self.graph.pack_target(target)]
        return self.graph.unpack_edge(edgeID)

    def __setitem__(self, target, edgeInfo):
        "Add edge from fromNode to target with edgeInfo"
        self.graph.d[self.fromNode][self.graph.pack_target(target)] \
             = self.graph.pack_edge(edgeInfo)
        if not hasattr(self.graph, 'sourceDB') or \
           (hasattr(self.graph, 'targetDB') and \
           self.graph.sourceDB == self.graph.targetDB):
            self.graph += target # ADD NEW NODE TO THE NODE DICT

    def __delitem__(self, target):
        "Delete edge from fromNode to target"
        try:
            del self.graph.d[self.fromNode][self.graph.pack_target(target)]
        except KeyError: # GENERATE A MORE INFORMATIVE ERROR MESSAGE
            raise KeyError('No edge from node to target')

    ######### CONVENIENCE METHODS THAT USE THE ACCESS METHODS ABOVE
    def __iadd__(self, target):
        "Add edge from fromNode to target with no edge-info"
        self[target] = None
        return self # THIS IS REQUIRED FROM iadd()!!

    def __isub__(self, target):
        "Delete edge from fromNode to target"
        self.__delitem__(target)
        return self # THIS IS REQUIRED FROM iadd()!!

    def edges(self):
        "Return iterator for accessing edges from fromNode"
        for target, edgeInfo in self.graph.d[self.fromNode].items():
            yield (self.graph.unpack_source(self.fromNode),
                   self.graph.unpack_target(target),
                   self.graph.unpack_edge(edgeInfo))

    def __len__(self):
        return len(self.graph.d[self.fromNode])

    def keys(self):
        return [k[1] for k in self.edges()] ##### ITERATORS

    def values(self):
        return [k[2] for k in self.edges()]

    def items(self):
        return [k[1:3] for k in self.edges()]

    def __iter__(self):
        for source, target, edgeInfo in self.edges():
            yield target

    def itervalues(self):
        for source, target, edgeInfo in self.edges():
            yield edgeInfo

    def iteritems(self):
        for source, target, edgeInfo in self.edges():
            yield target, edgeInfo

    __cmp__ = graph_cmp


class IDNodeDictWriteback(IDNodeDict):
    'forces writing of subdictionary in shelve opened without writeback=True'

    def __setitem__(self, target, edgeInfo):
        d = self.graph.d[self.fromNode]
        d[self.graph.pack_target(target)] = self.graph.pack_edge(edgeInfo)
        self.graph.d[self.fromNode] = d # WRITE IT BACK... REQUIRED FOR SHELVE
        self.graph += target # ADD NEW NODE TO THE NODE DICT

    def __delitem__(self, target):
        d = self.graph.d[self.fromNode]
        del d[self.graph.pack_target(target)]
        self.graph.d[self.fromNode] = d # WRITE IT BACK... REQUIRED FOR SHELVE


class IDNodeDictWriteNow(IDNodeDictWriteback):
    'opens shelve for writing, writes an item, immediately reopens'

    def __setitem__(self, target, edgeInfo):
        self.graph.d.reopen('w')
        IDNodeDictWriteback.__setitem__(self, target, edgeInfo)
        self.graph.d.reopen('w')

    def __delitem__(self, target):
        self.graph.d.reopen('w')
        IDNodeDictWriteback.__delitem__(self, target)
        self.graph.d.reopen('w')


class IDGraphEdges(object):
    '''provides iterator over edges as (source, target, edge) tuples
       and getitem[edge] --> [(source, target), ...]'''

    def __init__(self, g):
        self.g = g

    def __iter__(self):
        for d in self.g.itervalues():
            for edge in d.edges():
                yield edge

    def __getitem__(self, edge):
        l = []
        for sourceID, targetID in self.d[edge.id]:
            l.append((self.g.sourceDB[sourceID], self.g.targetDB[targetID]))
        return l

    def __call__(self):
        return self


class IDGraphEdgeDescriptor(object):
    'provides interface to edges on demand'

    def __get__(self, obj, objtype):
        return IDGraphEdges(obj)


def save_graph_db_refs(self, sourceDB=None, targetDB=None, edgeDB=None,
                       simpleKeys=False, unpack_edge=None,
                       edgeDictClass=None, graph=None, **kwargs):
    'apply kwargs to reference DB objects for this graph'
    if sourceDB is not None:
        self.sourceDB = sourceDB
    else:
        # No source DB, store keys as internal representation.
        simpleKeys = True
    if targetDB is not None:
        self.targetDB=targetDB
    if edgeDB is not None:
        self.edgeDB=edgeDB
    else: # just save the edge object as itself (not its ID)
        self.pack_edge = self.unpack_edge = lambda edge: edge
    if simpleKeys: # SWITCH TO USING TRIVIAL PACKING: OBJECT IS ITS OWN ID
        self.__class__ = self._IDGraphClass
    if unpack_edge is not None:
        self.unpack_edge = unpack_edge # UNPACKING METHOD OVERRIDES DEFAULT
    if graph is not None:
        self.graph = graph
    if edgeDictClass is not None:
        self.edgeDictClass = edgeDictClass


def graph_db_inverse_refs(self, edgeIndex=False):
    'return kwargs for inverse of this graph, or edge index of this graph'
    if edgeIndex: # TO CONSTRUCT AN EDGE INDEX
        db = ('edgeDB', 'sourceDB', 'targetDB')
    else: # DEFAULT: TO CONSTRUCT AN INVERSE MAPPING OF THE GRAPH
        db = ('targetDB', 'sourceDB', 'edgeDB')
    try:
        d = dict(sourceDB=getattr(self, db[0]), targetDB=getattr(self, db[1]))
        try:
            d['edgeDB'] = getattr(self, db[2]) # EDGE INFO IS OPTIONAL
        except AttributeError:
            pass
    except AttributeError:
        d = dict(simpleKeys=True) # NO SOURCE / TARGET DB, SO USE IDs AS KEYS
    try: # COPY THE LOCAL UNPACKING METHOD, IF ANY
        if not edgeIndex:
            d['unpack_edge'] = self.__dict__['unpack_edge']
    except KeyError:
        pass
    return d


def graph_setitem(self, node, target):
    "This method exists only to support g[n]+=o.  Do not use as g[n]=foo."
    node = self.pack_source(node)
    try:
        if node == target.fromNode:
            return
    except AttributeError:
        pass
    raise ValueError('Incorrect usage. Add edges using g[n]+=o or \
g[n][o]=edge.')


class Graph(object):
    """Top layer graph interface implemenation using proxy dict.
       Works with dict, shelve, any mapping interface."""
    edgeDictClass = IDNodeDict # DEFAULT EDGE DICT

    def __init__(self, saveDict=None, dictClass=dict, writeNow=False,
                 **kwargs):
        if saveDict is not None: # USE THE SUPPLIED STORAGE
            self.d = saveDict
        elif 'filename' in kwargs: # USE A SHELVE (BERKELEY DB)
            try:
                if kwargs['intKeys']: # ALLOW INT KEYS, HAVE TO USE IntShelve
                    self.d = IntShelve(writeback=False, **kwargs)
                else:
                    raise KeyError
            except KeyError:
                self.d = PicklableShelve(writeback=False, **kwargs)
            if writeNow:
                # Write immediately.
                self.edgeDictClass = IDNodeDictWriteNow
            else:
                # Use our own writeback.
                self.edgeDictClass = IDNodeDictWriteback
        else:
            self.d = dictClass()
        save_graph_db_refs(self, **kwargs)

    __getstate__ = classutil.standard_getstate ############### PICKLING METHODS
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(d='saveDict', sourceDB=0, targetDB=0, edgeDB=0,
                        edgeDictClass=0)
    add_standard_packing_methods(locals())  ############ PACK / UNPACK METHODS

    def close(self):
        '''If possible, close our dict.'''
        try:
            do_close = self.d.close
        except AttributeError:
            pass
        else:
            do_close()

    def __len__(self):
        return len(self.d)

    def __iter__(self):
        for node in self.d:
            yield self.unpack_source(node)

    def keys(self):
        return [k for k in self]

    def itervalues(self):
        for node in self.d:
            yield self.edgeDictClass(self, node)

    def values(self):
        return [v for v in self.itervalues()]

    def iteritems(self):
        for node in self.d:
            yield self.unpack_source(node), self.edgeDictClass(self, node)

    def items(self):
        return [v for v in self.iteritems()]

    edges = IDGraphEdgeDescriptor()

    def __iadd__(self, node):
        "Add node to graph with no edges"
        node = self.pack_source(node)
        if node not in self.d:
            self.d[node] = {} # INITIALIZE TOPLEVEL DICTIONARY
        return self # THIS IS REQUIRED FROM iadd()!!

    def __contains__(self, node):
        return self.pack_source(node) in self.d

    def __getitem__(self, node):
        if node in self:
            return self.edgeDictClass(self, self.pack_source(node))
        raise KeyError('node not in graph')
    __setitem__ = graph_setitem

    def __delitem__(self, node):
        "Delete node from graph."
        node = self.pack_source(node)
        # Grr, we really need to find all edges going to this node
        # and delete them.
        try:
            del self.d[node]  # DO STUFF TO REMOVE IT HERE...
        except KeyError:
            raise KeyError('Node not present in mapping.')

    def __isub__(self, node):
        "Delete node from graph"
        self.__delitem__(node)
        return self # THIS IS REQUIRED FROM isub()!!
    update = update_graph
    __cmp__ = graph_cmp

    def __del__(self):
        try:
            self.close()
        except classutil.FileAlreadyClosedError:
            pass

# NEED TO PROVIDE A REAL INVERT METHOD!!
##     def __invert__(self):
##         'get an interface to the inverse graph mapping'
##         try: # CACHED
##             return self._inverse
##         except AttributeError: # NEED TO CONSTRUCT INVERSE MAPPING
##             self._inverse = IDGraph(~(self.d), self.targetDB, self.sourceDB,
##                                     self.edgeDB)
##             self._inverse._inverse = self
##             return self._inverse
##
    def __hash__(self): # SO SCHEMA CAN INDEX ON GRAPHS...
        return id(self)


class IDGraph(Graph):
    add_trivial_packing_methods(locals())

Graph._IDGraphClass = IDGraph


class KeepUniqueDict(dict):
    'dict that blocks attempts to overwrite an existing key'

    def __setitem__(self, k, v):
        try:
            if self[k] is v:
                return # ALREADY SAVED.  NOTHING TO DO!
        except KeyError: # NOT PRESENT, SO JUST SAVE THE VALUE
            dict.__setitem__(self, k, v)
            return
        raise KeyError('attempt to overwrite existing key!')

    def __hash__(self):
        'ALLOW THIS OBJECT TO BE USED AS A KEY IN DICTS...'
        return id(self)

########NEW FILE########
__FILENAME__ = metabase

import datetime
import os
import pickle
import re
import sys
import UserDict
from StringIO import StringIO
from mapping import Collection, Mapping, Graph
from classutil import open_shelve, standard_invert, get_bound_subclass, \
     SourceFileName
from coordinator import XMLRPCServerBase


try:
    nonPortableClasses
except NameError: # DEFAULT LIST OF CLASSES NOT PORTABLE TO REMOTE CLIENTS
    nonPortableClasses = [SourceFileName]


class OneTimeDescriptor(object):
    'provides shadow attribute based on schema'

    def __init__(self, attrName, mdb, **kwargs):
        self.attr=attrName
        self.mdb = mdb

    def __get__(self, obj, objtype):
        try:
            resID = obj._persistent_id # GET ITS RESOURCE ID
        except AttributeError:
            raise AttributeError('attempt to access worldbase attr on \
                                 non-worldbase object')
        target = self.mdb.get_schema_attr(resID, self.attr) #get from mdb
        # Save in __dict__ to evade __setattr__.
        obj.__dict__[self.attr] = target
        return target


class ItemDescriptor(object):
    'provides shadow attribute for items in a db, based on schema'

    def __init__(self, attrName, mdb, invert=False, getEdges=False,
                 mapAttr=None, targetAttr=None, uniqueMapping=False, **kwargs):
        self.attr = attrName
        self.mdb = mdb
        self.invert = invert
        self.getEdges = getEdges
        self.mapAttr = mapAttr
        self.targetAttr = targetAttr
        self.uniqueMapping = uniqueMapping

    def get_target(self, obj):
        'return the mapping object for this schema relation'
        try:
            resID = obj.db._persistent_id # GET RESOURCE ID OF DATABASE
        except AttributeError:
            raise AttributeError('attempt to access worldbase attr on \
                                 non-worldbase object')
        targetDict = self.mdb.get_schema_attr(resID, self.attr)
        if self.invert:
            targetDict = ~targetDict
        if self.getEdges:
            targetDict = targetDict.edges
        return targetDict

    def __get__(self, obj, objtype):
        targetDict = self.get_target(obj)
        if self.mapAttr is not None: # USE mapAttr TO GET ID FOR MAPPING obj
            obj_id = getattr(obj, self.mapAttr)
            if obj_id is None: # None MAPS TO None, SO RETURN IMMEDIATELY
                return None # DON'T BOTHER CACHING THIS
            result = targetDict[obj_id] # MAP USING THE SPECIFIED MAPPING
        else:
            result = targetDict[obj] # NOW PERFORM MAPPING IN THAT RESOURCE...
        if self.targetAttr is not None:
            # Get attribute of the result.
            result = getattr(result, self.targetAttr)
        obj.__dict__[self.attr] = result # CACHE IN THE __dict__
        return result


class ItemDescriptorRW(ItemDescriptor):

    def __set__(self, obj, newTarget):
        if not self.uniqueMapping:
            raise WorldbaseSchemaError(
'''You attempted to directly assign to a graph mapping (x.graph = y)!
Instead, treat the graph like a dictionary: x.graph[y] = edgeInfo''')
        targetDict = self.get_target(obj)
        targetDict[obj] = newTarget
        obj.__dict__[self.attr] = newTarget # CACHE IN THE __dict__


class ForwardingDescriptor(object):
    'forward an attribute request to item from another container'

    def __init__(self, targetDB, attr):
        self.targetDB = targetDB # CONTAINER TO GET ITEMS FROM
        self.attr = attr # ATTRIBUTE TO MAP TO

    def __get__(self, obj, objtype):
        target = self.targetDB[obj.id] # GET target FROM CONTAINER
        return getattr(target, self.attr) # GET DESIRED ATTRIBUTE


class SpecialMethodDescriptor(object):
    'enables shadowing of special methods like __invert__'

    def __init__(self, attrName):
        self.attr = attrName

    def __get__(self, obj, objtype):
        try:
            return obj.__dict__[self.attr]
        except KeyError:
            raise AttributeError('%s has no method %s' % (obj, self.attr))


def addSpecialMethod(obj, attr, f):
    '''bind function f as special method attr on obj.
    obj cannot be an builtin or extension class
    (if so, just subclass it)'''
    import new
    m=new.instancemethod(f, obj, obj.__class__)
    try:
        if getattr(obj, attr) == m: # ALREADY BOUND TO f
            return # ALREADY BOUND, NOTHING FURTHER TO DO
    except AttributeError:
        pass
    else:
        raise AttributeError('%s already bound to a different function' % attr)
    setattr(obj, attr, m) # SAVE BOUND METHOD TO __dict__
    # This does forwarding.
    setattr(obj.__class__, attr, SpecialMethodDescriptor(attr))


def getInverseDB(self):
    'default shadow __invert__ method'
    return self.inverseDB # TRIGGER CONSTRUCTION OF THE TARGET RESOURCE


class WorldbaseNotPortableError(ValueError):
    '''indicates that object has a local data dependency and cannot be
    transferred to a remote client'''
    pass


class WorldbaseNotFoundError(KeyError):
    '''unable to find a loadable resource for the requested worldbase
    identifier from WORLDBASEPATH'''
    pass


class WorldbaseMismatchError(ValueError):
    '''_persistent_id attr on object no longer matches its assigned
    worldbase ID?!?'''
    pass


class WorldbaseEmptyError(ValueError):
    "user hasn't queued anything, so trying to save or rollback is an error"
    pass


class WorldbaseReadOnlyError(ValueError):
    'attempt to write data to a read-only resource database'
    pass


class WorldbaseSchemaError(ValueError):
    "attempt to set attribute to an object not in the database bound by schema"
    pass


class WorldbaseNoModuleError(pickle.PickleError):
    'attempt to pickle a class from a non-importable module'
    pass


class PygrPickler(pickle.Pickler):

    def persistent_id(self, obj):
        '''convert objects with _persistent_id to PYGR_ID strings
        during pickling'''
        import types
        try:
            # Check for unpicklable class (i.e. not loaded
            # via a module import).
            if isinstance(obj, types.TypeType) and \
               obj.__module__ == '__main__':
                raise WorldbaseNoModuleError(
'''You cannot pickle a class from __main__!
To make this class (%s) picklable, it must be loaded via a regular
import statement.''' % obj.__name__)
        except AttributeError:
            pass
        try:
            if not isinstance(obj, types.TypeType) and obj is not self.root:
                try:
                    return 'PYGR_ID:%s' % self.sourceIDs[id(obj)]
                except KeyError:
                    if obj._persistent_id is not None:
                        return 'PYGR_ID:%s' % obj._persistent_id
        except AttributeError:
            pass
        for klass in self.badClasses: # CHECK FOR LOCAL DEPENDENCIES
            if isinstance(obj, klass):
                raise WorldbaseNotPortableError(
'''this object has a local data dependency and cannnot be transferred
to a remote client''')
        return None

    def setRoot(self, obj, sourceIDs={}, badClasses=()):
        '''set obj as root of pickling tree: genuinely pickle it
        (not just its id)'''
        self.root = obj
        self.sourceIDs = sourceIDs
        self.badClasses = badClasses


class MetabaseServer(object):
    'simple XMLRPC resource database server'
    xmlrpc_methods = {'getResource': 0, 'registerServer': 0, 'delResource': 0,
                      'getName': 0, 'dir': 0, 'get_version': 0}
    _pygr_data_version = (0, 1, 0)

    def __init__(self, name, readOnly=True, downloadDB=None):
        self.name = name
        self.d = {}
        self.docs = {}
        self.downloadDB = {}
        self.downloadDocs = {}
        if readOnly: # LOCK THE INDEX.  DON'T ACCEPT FOREIGN DATA!!
            # Only allow these methods!
            self.xmlrpc_methods = {'getResource': 0, 'getName': 0, 'dir': 0,
                                   'get_version': 0}
        if downloadDB is not None:
            self.read_download_db(downloadDB)

    def read_download_db(self, filename, location='default'):
        'add the designated resource DB shelve to our downloadable resources'
        d = open_shelve(filename, 'r')
        for k, v in d.items():
            if k.startswith('__doc__.'): # SAVE DOC INFO FOR THIS ID
                self.downloadDocs[k[8:]] = v
            else: # SAVE OBJECT INFO
                self.downloadDB.setdefault(k, {})[location] = v
        d.close()

    def getName(self):
        'return layer name for this server'
        return self.name

    def get_db(self, download):
        if download: # USE SEPARATE DOWNLOAD DATABASE
            return (self.downloadDB, self.downloadDocs)
        else: # USE REGULAR XMLRPC SERVICES DATABASE
            return (self.d, self.docs)

    def getResource(self, id, download=False):
        'return dict of location:pickleData for requested ID'
        db, docs = self.get_db(download)
        try:
            d = db[id] # RETURN DICT OF PICKLED OBJECTS
        except KeyError:
            return '' # EMPTY STRING INDICATES FAILURE
        if id.startswith('SCHEMA.'): # THIS IS A REQUEST FOR SCHEMA INFO
            for location in d: # -schemaEdge DATA NOT SENDABLE BY XMLRPC
                try:
                    del d[location]['-schemaEdge']
                except KeyError:
                    pass
        else: # THIS IS A REGULAR RESOURCE REQUEST
            try: # PASS ITS DOCSTRING AS A SPECIAL ENTRY
                d['__doc__'] = docs[id]['__doc__']
            except KeyError:
                pass
        return d

    def registerServer(self, locationKey, serviceDict):
        '''add services in serviceDict to this server under the
        specified location'''
        n = 0
        for id, (infoDict, pdata) in serviceDict.items():
            self.d.setdefault(id, {})[locationKey] = pdata # SAVE RESOURCE
            if infoDict is not None:
                self.docs[id] = infoDict
            n += 1
        return n  # COUNT OF SUCCESSFULLY REGISTERED SERVICES

    def delResource(self, id, locationKey):
        'delete the specified resource under the specified location'
        try:
            del self.d[id][locationKey]
            if len(self.d[id]) == 0:
                del self.docs[id]
        except KeyError:
            pass
        return ''  # DUMMY RETURN VALUE FOR XMLRPC

    def dir(self, pattern, asDict=False, matchType='p', download=False):
        'return list or dict of resources matching the specified string'
        db, docs = self.get_db(download)
        if matchType == 'r':
            pattern = re.compile(pattern)
        l = []
        for name in db: # FIND ALL ITEMS WITH MATCHING NAME
            if matchType == 'p' and name.startswith(pattern) or \
               matchType == 'r' and pattern.search(name):
                l.append(name)
        if asDict: # RETURN INFO DICT FOR EACH ITEM
            d = {}
            for name in l:
                d[name] = docs.get(name, {})
            return d
        return l

    def get_version(self):
        return self._pygr_data_version


def raise_illegal_save(self, *l):
    raise WorldbaseReadOnlyError(
'''You cannot save data to a remote XMLRPC server.
Give a user-editable resource database as the first entry
in your WORLDBASEPATH!''')


class XMLRPCMetabase(object):
    'client interface to remote XMLRPC resource database'

    def __init__(self, url, mdb, **kwargs):
        from coordinator import get_connection
        self.server = get_connection(url, 'index')
        self.url=url
        self.mdb = mdb
        self.zoneName = self.server.getName()
        self.writeable = False

    def find_resource(self, id, download=False):
        'get pickledata,docstring for this resource ID from server'
        if download: # SPECIFICALLY ASK SERVER FOR DOWNLOADABLE RESOURCES
            d = self.server.getResource(id, download)
        else: # NORMAL MODE TO GET XMLRPC SERVICES
            d = self.server.getResource(id)
        if d == '':
            raise WorldbaseNotFoundError('resource %s not found' % id)
        try:
            docstring = d['__doc__']
            del d['__doc__']
        except KeyError:
            docstring = None
        for location, objdata in d.items(): # return the first resource found
            return objdata, docstring
        raise KeyError('unable to find %s from remote services' % id)

    def registerServer(self, locationKey, serviceDict):
        'forward registration to the server'
        return self.server.registerServer(locationKey, serviceDict)

    def getschema(self, id):
        'return dict of {attr: {args}}'
        d = self.server.getResource('SCHEMA.' + id)
        if d == '': # NO SCHEMA INFORMATION FOUND
            raise KeyError
        for schemaDict in d.values():
            return schemaDict # HAND BACK FIRST SCHEMA WE FIND
        raise KeyError

    def dir(self, pattern, matchType='p', asDict=False, download=False):
        'return list or dict of resources matching the specified string'
        if download:
            return self.server.dir(pattern, asDict, matchType, download)
        else:
            return self.server.dir(pattern, asDict, matchType)

    __setitem__ = raise_illegal_save # RAISE USEFUL EXPLANATORY ERROR MESSAGE
    __delitem__ = raise_illegal_save
    setschema = raise_illegal_save
    delschema = raise_illegal_save


class MySQLMetabase(object):
    '''To create a new resource table, call:
    MySQLMetabase("DBNAME.TABLENAME", mdb, createLayer="LAYERNAME")
    where DBNAME is the name of your database, TABLENAME is the name
    of the table you want to create, and LAYERNAME is the layer name
    you want to assign it'''
    _pygr_data_version = (0, 1, 0)

    def __init__(self, tablename, mdb, createLayer=None, newZone=None,
                 **kwargs):
        from sqlgraph import get_name_cursor, SQLGraph
        self.tablename, self.cursor, self.serverInfo = \
                get_name_cursor(tablename)
        self.mdb = mdb
        self.writeable = True
        self.rootNames = {}
        # Separate table for schema graph.
        schemaTable = self.tablename + '_schema'
        if createLayer is None:
            createLayer = newZone # use the new parameter
        if createLayer is not None: # CREATE DATABASE FROM SCRATCH
            creation_time = datetime.datetime.now()
            self.cursor.execute('drop table if exists %s' % self.tablename)
            self.cursor.execute('create table %s (pygr_id varchar(255) not \
                                null,location varchar(255) not null,docstring \
                                varchar(255),user varchar(255),creation_time \
                                datetime,pickle_size int,security_code bigint,\
                                info_blob text,objdata text not null,\
                                unique(pygr_id,location))' % self.tablename)
            self.cursor.execute('insert into %s (pygr_id,location,\
                                creation_time,objdata) values (%%s,%%s,%%s,\
                                %%s)' % self.tablename,
                                ('PYGRLAYERNAME', createLayer, creation_time,
                                 'a'))
            # Save version stamp.
            self.cursor.execute('insert into %s (pygr_id,location,objdata) \
                                values (%%s,%%s,%%s)' % self.tablename,
                                ('0version', '%d.%d.%d'
                                 % self._pygr_data_version, 'a'))
            self.zoneName = createLayer
            self.cursor.execute('drop table if exists %s' % schemaTable)
            self.cursor.execute('create table %s (source_id varchar(255) not \
                                null,target_id varchar(255),edge_id \
                                varchar(255),unique(source_id,target_id))'
                                % schemaTable)
        else:
            try:
                n = self.cursor.execute('select location from %s where \
                                        pygr_id=%%s' % self.tablename,
                                        ('PYGRLAYERNAME', ))
            except StandardError:
                print >>sys.stderr, '''%s
Database table %s appears to be missing or has no layer name!
To create this table, call
worldbase.MySQLMetabase("%s", createLayer=<LAYERNAME>)
where <LAYERNAME> is the layer name you want to assign it.
%s''' % ('!' * 40, self.tablename, self.tablename, '!' * 40)
                raise
            if n > 0:
                # Get layer name from the db.
                self.zoneName = self.cursor.fetchone()[0]
            if self.cursor.execute('select location from %s where pygr_id=%%s'
                                   % self.tablename, ('0root', )) > 0:
                for row in self.cursor.fetchall():
                    self.rootNames[row[0]] = None
                mdb.save_root_names(self.rootNames)
        self.graph = SQLGraph(schemaTable, self.cursor, attrAlias=
                              dict(source_id='source_id',
                                   target_id='target_id', edge_id='edge_id'),
                              simpleKeys=True, unpack_edge=SchemaEdge(self))

    def save_root_name(self, name):
        self.rootNames[name] = None
        self.cursor.execute('insert into %s (pygr_id,location,objdata) values \
                            (%%s,%%s,%%s)' % self.tablename, ('0root', name,
                                                              'a'))

    def find_resource(self, id, download=False):
        'get construction rule from mysql, and attempt to construct'
        self.cursor.execute('select location,objdata,docstring from %s where \
                            pygr_id=%%s' % self.tablename, (id, ))
        for location, objdata, docstring in self.cursor.fetchall():
            return objdata, docstring # return first resource found
        raise WorldbaseNotFoundError('unable to construct %s from remote \
                                     services')

    def __setitem__(self, id, obj):
        'add an object to this resource database'
        s = dumps(obj) # PICKLE obj AND ITS DEPENDENCIES
        d = get_info_dict(obj, s)
        self.cursor.execute('replace into %s (pygr_id,location,docstring,user,\
                            creation_time,pickle_size,objdata) values (%%s,\
                            %%s,%%s,%%s,%%s,%%s,%%s)' % self.tablename,
                            (id, 'mysql:' + self.tablename, obj.__doc__,
                             d['user'], d['creation_time'], d['pickle_size'],
                             s))
        root = id.split('.')[0]
        if root not in self.rootNames:
            self.save_root_name(root)

    def __delitem__(self, id):
        'delete this resource and its schema rules'
        if self.cursor.execute('delete from %s where pygr_id=%%s'
                               % self.tablename, (id, )) < 1:
            raise WorldbaseNotFoundError('no resource %s in this database'
                                         % id)

    def registerServer(self, locationKey, serviceDict):
        'register the specified services to mysql database'
        n = 0
        for id, (d, pdata) in serviceDict.items():
            n+=self.cursor.execute('replace into %s (pygr_id,location,\
                                   docstring,user,creation_time,pickle_size,\
                                   objdata) values (%%s,%%s,%%s,%%s,%%s,%%s,\
                                   %%s)' % self.tablename,
                                   (id, locationKey, d['__doc__'], d['user'],
                                    d['creation_time'], d['pickle_size'],
                                    pdata))
        return n

    def setschema(self, id, attr, kwargs):
        'save a schema binding for id.attr --> targetID'
        if not attr.startswith('-'): # REAL ATTRIBUTE
            targetID = kwargs['targetID'] # RAISES KeyError IF NOT PRESENT
        kwdata = dumps(kwargs)
        self.cursor.execute('replace into %s (pygr_id,location,objdata) \
                            values (%%s,%%s,%%s)' % self.tablename,
                            ('SCHEMA.' + id, attr, kwdata))

    def delschema(self, id, attr):
        'delete schema binding for id.attr'
        self.cursor.execute('delete from %s where pygr_id=%%s and location=%%s'
                            % self.tablename, ('SCHEMA.' + id, attr))

    def getschema(self, id):
        'return dict of {attr:{args}}'
        d = {}
        self.cursor.execute('select location,objdata from %s where pygr_id=%%s'
                            % self.tablename, ('SCHEMA.' + id, ))
        for attr, objData in self.cursor.fetchall():
            d[attr] = self.mdb.loads(objData)
        return d

    def dir(self, pattern, matchType='p', asDict=False, download=False):
        'return list or dict of resources matching the specified string'

        if matchType == 'r':
            self.cursor.execute('select pygr_id,docstring,user,creation_time,\
                                pickle_size from %s where pygr_id regexp %%s'
                                % self.tablename, (pattern, ))
        elif matchType == 'p':
            self.cursor.execute('select pygr_id,docstring,user,creation_time,\
                                pickle_size from %s where pygr_id like %%s'
                                % self.tablename, (pattern + '%', ))
        else:
            # Exit now to avoid fetching rows with no query executed
            if asDict:
                return {}
            else:
                return []

        d = {}
        for l in self.cursor.fetchall():
            d[l[0]] = dict(__doc__=l[1], user=l[2], creation_time=l[3],
                           pickle_size=l[4])
        if asDict:
            return d
        else:
            return [name for name in d]


class SchemaEdge(object):
    'provides unpack_edge method for schema graph storage'

    def __init__(self, schemaDB):
        self.schemaDB = schemaDB

    def __call__(self, edgeID):
        'get the actual schema object describing this ID'
        return self.schemaDB.getschema(edgeID)['-schemaEdge']


class ResourceDBGraphDescr(object):
    'this property provides graph interface to schema'

    def __get__(self, obj, objtype):
        g = Graph(filename=obj.dbpath + '_schema', mode='cw', writeNow=True,
                  simpleKeys=True, unpack_edge=SchemaEdge(obj))
        obj.graph = g
        return g


class ShelveMetabase(object):
    '''BerkeleyDB-based storage of worldbase resource databases, using
    the python shelve module.  Users will not need to create instances
    of this class themselves, as worldbase automatically creates one for
    each appropriate entry in your WORLDBASEPATH; if the corresponding
    database file does not already exist, it is automatically created
    for you.'''
    _pygr_data_version = (0, 1, 0)
    graph = ResourceDBGraphDescr() # INTERFACE TO SCHEMA GRAPH

    def __init__(self, dbpath, mdb, mode='r', newZone=None, **kwargs):
        import anydbm
        self.dbpath = os.path.join(dbpath, '.pygr_data') # CONSTRUCT FILENAME
        self.mdb = mdb
        self.writeable = True # can write to this storage
        self.zoneName = None
        try: # OPEN DATABASE FOR READING
            self.db = open_shelve(self.dbpath, mode)
            try:
                mdb.save_root_names(self.db['0root'])
            except KeyError:
                pass
            try:
                self.zoneName = self.db['0zoneName']
            except KeyError:
                pass
        except anydbm.error: # CREATE NEW FILE IF NEEDED
            self.db = open_shelve(self.dbpath, 'c')
            self.db['0version'] = self._pygr_data_version # SAVE VERSION STAMP
            self.db['0root'] = {}
            if newZone is not None:
                self.db['0zoneName'] = newZone
                self.zoneName = newZone

    def reopen(self, mode):
        self.db.close()
        self.db = open_shelve(self.dbpath, mode)

    def find_resource(self, resID, download=False):
        'get an item from this resource database'
        objdata = self.db[resID] # RAISES KeyError IF NOT PRESENT
        try:
            return objdata, self.db['__doc__.' + resID]['__doc__']
        except KeyError:
            return objdata, None

    def __setitem__(self, resID, obj):
        'add an object to this resource database'
        s = dumps(obj) # PICKLE obj AND ITS DEPENDENCIES
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        try:
            self.db[resID] = s # SAVE TO OUR SHELVE FILE
            self.db['__doc__.' + resID] = get_info_dict(obj, s)
            root = resID.split('.')[0] # SEE IF ROOT NAME IS IN THIS SHELVE
            d = self.db.get('0root', {})
            if root not in d:
                d[root] = None # ADD NEW ENTRY
                self.db['0root'] = d # SAVE BACK TO SHELVE
        finally:
            self.reopen('r') # REOPEN READ-ONLY

    def __delitem__(self, resID):
        'delete this item from the database, with a modicum of safety'
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        try:
            try:
                del self.db[resID] # DELETE THE SPECIFIED RULE
            except KeyError:
                raise WorldbaseNotFoundError('ID %s not found in %s'
                                            % (resID, self.dbpath))
            try:
                del self.db['__doc__.' + resID]
            except KeyError:
                pass
        finally:
            self.reopen('r') # REOPEN READ-ONLY

    def dir(self, pattern, matchType='p', asDict=False, download=False):
        'generate all item IDs matching the specified pattern'
        if matchType == 'r':
            pattern = re.compile(pattern)
        l = []
        for name in self.db:
            if matchType == 'p' and name.startswith(pattern) or \
               matchType == 'r' and pattern.search(name):
                l.append(name)
        if asDict:
            d = {}
            for name in l:
                d[name] = self.db.get('__doc__.' + name, None)
            return d
        return l

    def setschema(self, resID, attr, kwargs):
        'save a schema binding for resID.attr --> targetID'
        if not attr.startswith('-'): # REAL ATTRIBUTE
            targetID = kwargs['targetID'] # RAISES KeyError IF NOT PRESENT
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        d = self.db.get('SCHEMA.' + resID, {})
        d[attr] = kwargs # SAVE THIS SCHEMA RULE
        self.db['SCHEMA.' + resID] = d # FORCE shelve TO RESAVE BACK
        self.reopen('r')  # REOPEN READ-ONLY

    def getschema(self, resID):
        'return dict of {attr:{args}}'
        return self.db['SCHEMA.' + resID]

    def delschema(self, resID, attr):
        'delete schema binding for resID.attr'
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        d=self.db['SCHEMA.' + resID]
        del d[attr]
        self.db['SCHEMA.' + resID] = d # FORCE shelve TO RESAVE BACK
        self.reopen('r')  # REOPEN READ-ONLY

    def __del__(self):
        'close the shelve file when finished'
        self.db.close()


def dumps(obj, **kwargs):
    'pickle to string, using persistent ID encoding'
    src = StringIO()
    pickler = PygrPickler(src) # NEED OUR OWN PICKLER, TO USE persistent_id
    # Root of pickle tree: save even if persistent_id.
    pickler.setRoot(obj, **kwargs)
    pickler.dump(obj) # PICKLE IT
    return src.getvalue() # RETURN THE PICKLED FORM AS A STRING


def get_info_dict(obj, pickleString):
    'get dict of standard info about a resource'
    d = dict(creation_time=datetime.datetime.now(),
             pickle_size=len(pickleString), __doc__=obj.__doc__)
    try:
        d['user'] = os.environ['USER']
    except KeyError:
        d['user'] = None
    return d


class MetabaseBase(object):

    def persistent_load(self, persid):
        'check for PYGR_ID:... format and return the requested object'
        if persid.startswith('PYGR_ID:'):
            return self(persid[8:]) # RUN OUR STANDARD RESOURCE REQUEST PROCESS
        else: # UNKNOWN PERSISTENT ID... NOT FROM PYGR!
            raise pickle.UnpicklingError, 'Invalid persistent ID %s' % persid

    def load(self, resID, objdata, docstring):
        'load the pickled data and all its dependencies'
        obj = self.loads(objdata)
        obj.__doc__ = docstring
        if hasattr(obj, '_saveLocalBuild') and obj._saveLocalBuild:
            saver = self.writer.saver # mdb in which to record local copy
            # SAVE AUTO BUILT RESOURCE TO LOCAL PYGR.DATA
            hasPending = saver.has_pending() # any pending transaction?
            saver.add_resource(resID, obj) # add to queue for commit
            obj._saveLocalBuild = False # NO NEED TO SAVE THIS AGAIN
            if hasPending:
                print >>sys.stderr, \
'''Saving new resource %s to local worldbase...
You must use worldbase.commit() to commit!
You are seeing this message because you appear to be in the middle
of a worldbase transaction.  Ordinarily worldbase would automatically commit
this new downloaded resource, but doing so now would also commit your pending
transaction, which you may not be ready to do!''' % resID
            else: # automatically save new resource
                saver.save_pending() # commit it
        else: # NORMAL USAGE
            obj._persistent_id = resID  # MARK WITH ITS PERSISTENT ID
        self.resourceCache[resID] = obj # SAVE TO OUR CACHE
        self.bind_schema(resID, obj) # BIND SHADOW ATTRIBUTES IF ANY
        return obj

    def loads(self, data):
        'unpickle from string, using persistent ID expansion'
        src = StringIO(data)
        unpickler = pickle.Unpickler(src)
        # We provide persistent lookup.
        unpickler.persistent_load = self.persistent_load
        obj = unpickler.load() # ACTUALLY UNPICKLE THE DATA
        return obj

    def __call__(self, resID, debug=None, download=None, *args, **kwargs):
        'get the requested resource ID by searching all databases'
        try:
            return self.resourceCache[resID] # USE OUR CACHED OBJECT
        except KeyError:
            pass
        debug_state = self.debug # SAVE ORIGINAL STATE
        download_state = self.download
        if debug is not None:
            self.debug = debug
        if download is not None: # apply the specified download mode
            self.download = download
        else: # just use our current download mode
            download = self.download
        try: # finally... TO RESTORE debug STATE EVEN IF EXCEPTION OCCURS.
            self.update(debug=self.debug, keepCurrentPath=True) # load if empty
            for objdata, docstr in self.find_resource(resID, download):
                try:
                    obj = self.load(resID, objdata, docstr)
                    break
                except (KeyError, IOError):
                    # Not in this DB; files not accessible...
                    if self.debug: # PASS ON THE ACTUAL ERROR IMMEDIATELY
                        raise
        finally: # RESTORE STATE BEFORE RAISING ANY EXCEPTION
            self.debug = debug_state
            self.download = download_state
        self.resourceCache[resID] = obj # save to our cache
        return obj

    def bind_schema(self, resID, obj):
        'if this resource ID has any schema, bind its attrs to class'
        try:
            schema = self.getschema(resID)
        except KeyError:
            return # NO SCHEMA FOR THIS OBJ, SO NOTHING TO DO
        self.resourceCache.schemaCache[resID] = schema # cache for speed
        for attr, rules in schema.items():
            if not attr.startswith('-'): # only bind real attributes
                self.bind_property(obj, attr, **rules)

    def bind_property(self, obj, attr, itemRule=False, **kwargs):
        'create a descriptor for the attr on the appropriate obj class'
        try: # SEE IF OBJECT TELLS US TO SKIP THIS ATTRIBUTE
            return obj._ignoreShadowAttr[attr] # IF PRESENT, NOTHING TO DO
        except (AttributeError, KeyError):
            pass # PROCEED AS NORMAL
        if itemRule: # SHOULD BIND TO ITEMS FROM obj DATABASE
            # Class used for constructing items.
            targetClass = get_bound_subclass(obj, 'itemClass')
            descr = ItemDescriptor(attr, self, **kwargs)
        else: # SHOULD BIND DIRECTLY TO obj VIA ITS CLASS
            targetClass = get_bound_subclass(obj)
            descr = OneTimeDescriptor(attr, self, **kwargs)
        setattr(targetClass, attr, descr) # BIND descr TO targetClass.attr
        if itemRule:
            try: # BIND TO itemSliceClass TOO, IF IT EXISTS...
                targetClass = get_bound_subclass(obj, 'itemSliceClass')
            except AttributeError:
                pass # NO itemSliceClass, SO SKIP
            else: # BIND TO itemSliceClass
                setattr(targetClass, attr, descr)
        if attr == 'inverseDB': # ADD SHADOW __invert__ TO ACCESS THIS
            addSpecialMethod(obj, '__invert__', getInverseDB)

    def get_schema_attr(self, resID, attr):
        'actually retrieve the desired schema attribute'
        try: # GET SCHEMA FROM CACHE
            schema = self.resourceCache.schemaCache[resID]
        except KeyError:
            # Hmm, it should be cached! Obtain from resource DB and cache.
            schema = self.getschema(resID)
            self.resourceCache.schemaCache[resID] = schema
        try:
            schema = schema[attr] # GET SCHEMA FOR THIS SPECIFIC ATTRIBUTE
        except KeyError:
            raise AttributeError('no worldbase schema info for %s.%s' \
                                 % (resID, attr))
        targetID = schema['targetID'] # GET THE RESOURCE ID
        return self(targetID) # actually load the resource

    def add_root_name(self, name):
        'add name to the root of our data namespace and schema namespace'
        # This forces the root object to add name if not present.
        getattr(self.Data, name)
        getattr(self.Schema, name)

    def save_root_names(self, rootNames):
        'add set of names to our namespace root'
        for name in rootNames:
            self.add_root_name(name)

    def clear_cache(self):
        'clear all resources from cache'
        self.resourceCache.clear()

    def get_writer(self):
        'return writeable mdb if available, or raise exception'
        try:
            return self.writer
        except AttributeError:
            raise WorldbaseReadOnlyError('this metabase is read-only!')

    def add_resource(self, resID, obj=None):
        """assign obj as the specified resource ID to our metabase.
        if obj is None, treat resID as a dictionary whose keys are
        resource IDs and values are the objects to save."""
        if obj is None:
            self.get_writer().saver.add_resource_dict(resID)
        else:
            self.get_writer().saver.add_resource(resID, obj)

    def delete_resource(self, resID):
        'delete specified resource ID from our metabase'
        self.get_writer().saver.delete_resource(resID)

    def commit(self):
        'save any pending resource assignments and schemas'
        self.get_writer().saver.save_pending()

    def rollback(self):
        'discard any pending resource assignments and schemas'
        self.get_writer().saver.rollback()

    def queue_schema_obj(self, schemaPath, attr, schemaObj):
        'add a schema to the list of pending schemas to commit'
        self.get_writer().saver.queue_schema_obj(schemaPath, attr, schemaObj)

    def add_schema(self, resID, schemaObj):
        'assign a schema relation object to a worldbase resource name'
        l = resID.split('.')
        schemaPath = SchemaPath(self, '.'.join(l[:-1]))
        setattr(schemaPath, l[-1], schemaObj)

    def list_pending(self):
        return self.get_writer().saver.list_pending()


class Metabase(MetabaseBase):

    def __init__(self, dbpath, resourceCache, zoneDict=None, parent=None,
                 **kwargs):
        '''zoneDict provides a mechanism for the caller to request information
        about what type of metabase this dbpath mapped to.  zoneDict must
        be a dict'''
        self.parent = parent
        self.Schema = SchemaPath(self)
        self.Data = ResourceRoot(self) # root of namespace
        self.resourceCache = resourceCache
        self.debug = True # single mdb should expose all errors
        self.download = False
        if zoneDict is None: # user doesn't want zoneDict info
            zoneDict = {} # use a dummy dict, disposable
        if dbpath.startswith('http://'):
            storage = XMLRPCMetabase(dbpath, self, **kwargs)
            if 'remote' not in zoneDict:
                zoneDict['remote'] = self
        elif dbpath.startswith('mysql:'):
            storage = MySQLMetabase(dbpath[6:], self, **kwargs)
            if 'MySQL' not in zoneDict:
                zoneDict['MySQL'] = self
        else: # TREAT AS LOCAL FILEPATH
            dbpath = os.path.expanduser(dbpath)
            storage = ShelveMetabase(dbpath, self, **kwargs)
            if dbpath == os.path.expanduser('~') or \
               dbpath.startswith(os.path.expanduser('~') + os.sep):
                if 'my' not in zoneDict:
                    zoneDict['my'] = self
            elif os.path.isabs(dbpath):
                if 'system' not in zoneDict:
                    zoneDict['system'] = self
            elif dbpath.split(os.sep)[0] == os.curdir:
                if 'here' not in zoneDict:
                    zoneDict['here'] = self
            elif 'subdir' not in zoneDict:
                zoneDict['subdir'] = self
        self.storage = storage
        if storage.zoneName is not None and storage.zoneName not in zoneDict:
            zoneDict[storage.zoneName] = self  # record this zone name
        if storage.writeable:
            self.writeable = True
            self.saver = ResourceSaver(self)
            self.writer = self # record downloaded resources here
        else:
            self.writeable = False

    def update(self, worldbasePath=None, debug=None, keepCurrentPath=False):
        if not keepCurrentPath: # metabase has fixed path
            raise ValueError('You cannot change the path of a Metabase')

    def find_resource(self, resID, download=False):
        yield self.storage.find_resource(resID, download)

    def get_pending_or_find(self, resID, **kwargs):
        'find resID even if only pending (not actually saved yet)'
        try: # 1st LOOK IN PENDING QUEUE
            return self.saver.pendingData[resID]
        except KeyError:
            pass
        return self(resID, **kwargs)

    def getschema(self, resID):
        'return dict of {attr: {args}} or KeyError if not found'
        return self.storage.getschema(resID)

    def save_root_names(self, rootNames):
        if self.parent is not None: # add names to parent's namespace as well
            self.parent.save_root_names(rootNames)
        MetabaseBase.save_root_names(self, rootNames) # call the generic method

    def saveSchema(self, resID, attr, args):
        '''save an attribute binding rule to the schema; DO NOT use this
        internal interface unless you know what you are doing!'''
        self.storage.setschema(resID, attr, args)

    def saveSchemaEdge(self, schema):
        'save schema edge to schema graph'
        self.saveSchema(schema.name, '-schemaEdge', schema)
        self.storage.graph += schema.sourceDB # ADD NODE TO SCHEMA GRAPH
        # Edge
        self.storage.graph[schema.sourceDB][schema.targetDB] = schema.name

    def dir(self, pattern='', matchType='p', asDict=False, download=False):
        return self.storage.dir(pattern, matchType, asDict=asDict,
                            download=download)


class ZoneDict(UserDict.DictMixin):
    'interface to current zones'

    def __init__(self, mdbList):
        self.mdbList = mdbList

    def __getitem__(self, zoneName):
        self.mdbList.update(keepCurrentPath=True) # make sure metabases loaded
        return self.mdbList.zoneDict[zoneName]

    def keys(self):
        self.mdbList.update(keepCurrentPath=True) # make sure metabases loaded
        return self.mdbList.zoneDict.keys()

    def copy(self):
        self.mdbList.update(keepCurrentPath=True) # make sure metabases loaded
        return self.mdbList.zoneDict.copy()


class MetabaseList(MetabaseBase):
    '''Primary interface for worldbase resource database access.
    A single instance of this class is created upon import of the
    worldbase module, accessible as worldbase.getResource.  Users
    normally will have no need to create additional instances of this
    class themselves.'''
    # DEFAULT WORLDBASEPATH: HOME, CURRENT DIR, XMLRPC IN THAT ORDER
    defaultPath = ['~', '.', 'http://biodb2.bioinformatics.ucla.edu:5000']

    def __init__(self, worldbasePath=None, resourceCache=None, separator=',',
                 mdbArgs={}):
        '''initializes attrs; does not connect to metabases'''
        if resourceCache is None: # create a cache for loaded resources
            resourceCache = ResourceCache()
        self.resourceCache = resourceCache
        self.mdb = None
        self.mdbArgs = mdbArgs
        self.zoneDict = {}
        self.zones = ZoneDict(self) # interface to dict of zones
        self.worldbasePath = worldbasePath
        self.separator = separator
        self.Schema = SchemaPath(self)
        self.Data = ResourceRoot(self, zones=self.zones) # root of namespace
        self.debug = False # if one load attempt fails, try other metabases
        self.download = False
        self.ready = False

    def get_writer(self):
        'ensure that metabases are loaded, before looking for our writer'
        self.update(keepCurrentPath=True) # make sure metabases loaded
        return MetabaseBase.get_writer(self) # proceed as usual

    def find_resource(self, resID, download=False):
        'search our metabases for pickle string and docstr for resID'
        for mdb in self.mdb:
            try:
                yield mdb.find_resource(resID, download).next()
            except KeyError: # not in this db
                pass
        raise WorldbaseNotFoundError('unable to find %s in WORLDBASEPATH'
                                     % resID)

    def get_worldbase_path(self):
        'get environment var, or default in that order'
        try:
            return os.environ['WORLDBASEPATH']
        except KeyError:
            try:
                return os.environ['PYGRDATAPATH']
            except KeyError:
                return self.separator.join(self.defaultPath)

    def update(self, worldbasePath=None, debug=None, keepCurrentPath=False,
               mdbArgs=None):
        'get the latest list of resource databases'
        if keepCurrentPath: # only update if self.worldbasePath is None
            worldbasePath = self.worldbasePath
        if worldbasePath is None: # get environment var or default
            worldbasePath = self.get_worldbase_path()
        if debug is None:
            debug = self.debug
        if mdbArgs is None:
            mdbArgs = self.mdbArgs
        if not self.ready or self.worldbasePath != worldbasePath: # reload
            self.worldbasePath = worldbasePath
            try: # disconnect from previous writeable interface if any
                del self.writer
            except AttributeError:
                pass
            self.mdb = []
            try: # default: we don't have a writeable mdb to save data in
                del self.writer
            except AttributeError:
                pass
            self.zoneDict = {}
            for dbpath in worldbasePath.split(self.separator):
                try: # connect to metabase
                    mdb = Metabase(dbpath, self.resourceCache, self.zoneDict,
                                   self, **mdbArgs)
                except (KeyboardInterrupt, SystemExit):
                    raise # DON'T TRAP THESE CONDITIONS
                # FORCED TO ADOPT THIS STRUCTURE BECAUSE xmlrpc RAISES
                # socket.gaierror WHICH IS NOT A SUBCLASS OF StandardError...
                # SO I CAN'T JUST TRAP StandardError, UNFORTUNATELY...
                except: # trap errors and continue to next metabase
                    if debug:
                        raise # expose the error immediately
                    else: # warn the user but keep going...
                        import traceback
                        traceback.print_exc(10, sys.stderr)
                        print >>sys.stderr, '''
WARNING: error accessing metabase %s.  Continuing...''' % dbpath
                else: # NO PROBLEM, SO ADD TO OUR RESOURCE DB LIST
                    # Save to our list of resource databases.
                    self.mdb.append(mdb)
                    if mdb.writeable and not hasattr(self, 'writer'):
                        self.writer = mdb # record as place to save resources
            self.ready = True # metabases successfully loaded

    def get_pending_or_find(self, resID, **kwargs):
        'find resID even if only pending (not actually saved yet)'
        for mdb in self.mdb:
            try: # 1st LOOK IN PENDING QUEUE
                return mdb.saver.pendingData[resID]
            except KeyError:
                pass
        return self(resID, **kwargs)

    def registerServer(self, locationKey, serviceDict):
        'register the serviceDict with the first index server in WORLDBASEPATH'
        for mdb in self.mdb:
            if hasattr(mdb.storage, 'registerServer'):
                n = mdb.storage.registerServer(locationKey, serviceDict)
                if n == len(serviceDict):
                    return n
        raise ValueError('unable to register services.  Check WORLDBASEPATH')

    def getschema(self, resID):
        'search our resource databases for schema info for the desired ID'
        for mdb in self.mdb:
            try:
                return mdb.getschema(resID) # TRY TO OBTAIN FROM THIS DATABASE
            except KeyError:
                pass # NOT IN THIS DB
        raise KeyError('no schema info available for ' + resID)

    def dir(self, pattern='', matchType='p', asDict=False, download=False):
        'get list or dict of resources beginning with the specified string'
        self.update(keepCurrentPath=True) # make sure metabases loaded
        results = []
        for mdb in self.mdb:
            results.append(mdb.dir(pattern, matchType, asDict=asDict,
                                   download=download))
        if asDict: # merge result dictionaries
            d = {}
            results.reverse() # give first results highest precedence
            for subdir in results:
                d.update(subdir)
            return d
        else: # simply remove redundancy from results
            d = {}
            for l in results:
                filter(d.setdefault, l) # add all entries to dict
            results = d.keys()
            results.sort()
            return results


class ResourceCache(dict):
    'provide one central repository of loaded resources & schema info'

    def __init__(self):
        dict.__init__(self)
        self.schemaCache = {}

    def clear(self):
        dict.clear(self) # clear our dictionary
        self.schemaCache.clear() #


class ResourceSaver(object):
    'queues new resources until committed to our mdb'

    def __init__(self, mdb):
        self.clear_pending()
        self.mdb = mdb

    def clear_pending(self):
        self.pendingData = {} # CLEAR THE PENDING QUEUE
        self.pendingSchema = {} # CLEAR THE PENDING QUEUE
        self.lastData = {}
        self.lastSchema = {}
        self.rollbackData = {} # CLEAR THE ROLLBACK CACHE

    def check_docstring(self, obj):
        '''enforce requirement for docstring, by raising exception
        if not present'''
        try:
            if obj.__doc__ is None or (hasattr(obj.__class__, '__doc__') and
                                       obj.__doc__==obj.__class__.__doc__):
                raise AttributeError
        except AttributeError:
            raise ValueError('to save a resource object, you MUST give it a \
                             __doc__ string attribute describing it!')

    def add_resource(self, resID, obj):
        'queue the object for saving to our metabase as <resID>'
        self.check_docstring(obj)
        obj._persistent_id = resID # MARK OBJECT WITH ITS PERSISTENT ID
        self.pendingData[resID] = obj # ADD TO QUEUE
        try:
            self.rollbackData[resID] = self.mdb.resourceCache[resID]
        except KeyError:
            pass
        self.cache_if_appropriate(resID, obj)

    def cache_if_appropriate(self, resID, obj):
        try:
            if obj._worldbase_no_cache:
                return # do not cache this object; it is not ready to use!!
        except AttributeError:
            pass
        self.mdb.resourceCache[resID] = obj # SAVE TO OUR CACHE

    def add_resource_dict(self, d):
        'queue a dict of name:object pairs for saving to metabase'
        for k, v in d.items():
            self.add_resource(k, v)

    def queue_schema_obj(self, schemaPath, attr, schemaObj):
        'add a schema object to the queue for saving to our metabase'
        resID = schemaPath.getPath(attr) # GET STRING ID
        self.pendingSchema[resID] = (schemaPath, attr, schemaObj)

    def save_resource(self, resID, obj):
        'save the object as <id>'
        self.check_docstring(obj)
        if obj._persistent_id != resID:
            raise WorldbaseMismatchError(
'''The _persistent_id attribute for %s has changed!
If you changed it, shame on you!  Otherwise, this should not happen, so report
the reproducible steps to this error message as a bug report.''' % resID)
        # Finally, save the object to the database.
        self.mdb.storage[resID] = obj
        self.cache_if_appropriate(resID, obj) # SAVE TO OUR CACHE

    def has_pending(self):
        'return True if there are resources pending to be committed'
        return len(self.pendingData) > 0 or len(self.pendingSchema) > 0

    def save_pending(self):
        'save any pending worldbase resources and schema'
        if len(self.pendingData) > 0 or len(self.pendingSchema) > 0:
            d = self.pendingData
            schemaDict = self.pendingSchema
        else:
            raise WorldbaseEmptyError('there is no data queued for saving!')
        for resID, obj in d.items(): # now save the data
            self.save_resource(resID, obj)
        for schemaPath, attr, schemaObj in schemaDict.values():# save schema
            schemaObj.saveSchema(schemaPath, attr, self.mdb) # save each rule
        self.clear_pending() # FINALLY, CLEAN UP...
        self.lastData = d # keep as a historical record
        self.lastSchema = schemaDict

    def list_pending(self):
        'return tuple of pending data dictionary, pending schema'
        return list(self.pendingData), list(self.pendingSchema)

    def rollback(self):
        'dump any pending data without saving, and restore state of cache'
        if len(self.pendingData) == 0 and len(self.pendingSchema) == 0:
            raise WorldbaseEmptyError('there is no data queued for saving!')
        # Restore the rollback queue.
        self.mdb.resourceCache.update(self.rollbackData)
        self.clear_pending()

    def delete_resource(self, resID): # incorporate this into commit-process?
        'delete the specified resource from resourceCache, saver and schema'
        del self.mdb.storage[resID] # delete from the resource database
        try:
            del self.mdb.resourceCache[resID] # delete from cache if exists
        except KeyError:
            pass
        try:
            del self.pendingData[resID] # delete from queue if exists
        except KeyError:
            pass
        self.delSchema(resID)

    def delSchema(self, resID):
        'delete schema bindings TO and FROM this resource ID'
        storage = self.mdb.storage
        try:
            d = storage.getschema(resID) # GET THE EXISTING SCHEMA
        except KeyError:
            return # no schema stored for this object so nothing to do...
        # This is more aggressive than needed... Could be refined.
        self.mdb.resourceCache.schemaCache.clear()
        for attr, obj in d.items():
            if attr.startswith('-'): # A SCHEMA OBJECT
                obj.delschema(storage) # DELETE ITS SCHEMA RELATIONS
            storage.delschema(resID, attr) # delete attribute schema rule

    def __del__(self):
        try:
            self.save_pending() # SEE WHETHER ANY DATA NEEDS SAVING
            print >>sys.stderr, '''
WARNING: saving worldbase pending data that you forgot to save...
Remember in the future, you must issue the command worldbase.commit() to save
your pending worldbase resources to your resource database(s), or alternatively
worldbase.rollback() to dump those pending data without saving them.
It is a very bad idea to rely on this automatic attempt to save your
forgotten data, because it is possible that the Python interpreter
may never call this function at exit (for details see the atexit module
docs in the Python Library Reference).'''
        except WorldbaseEmptyError:
            pass


class ResourceServer(XMLRPCServerBase):
    'serves resources that can be transmitted on XMLRPC'

    def __init__(self, mdb, name, serverClasses=None, clientHost=None,
                 withIndex=True, excludeClasses=None, downloadDB=None,
                 resourceDict=None, **kwargs):
        'construct server for the designated classes'
        XMLRPCServerBase.__init__(self, name, **kwargs)
        self.mdb = mdb
        if resourceDict is None:
            resourceDict = mdb.resourceCache
        if excludeClasses is None: # DEFAULT: NO POINT IN SERVING SQL TABLES...
            from sqlgraph import SQLTableBase, SQLGraphClustered
            excludeClasses = [SQLTableBase, SQLGraphClustered]
        if serverClasses is None: # DEFAULT TO ALL CLASSES WE KNOW HOW TO SERVE
            from seqdb import SequenceFileDB, BlastDB, \
                 XMLRPCSequenceDB, BlastDBXMLRPC, \
                 AnnotationDB, AnnotationClient, AnnotationServer
            serverClasses=[(SequenceFileDB, XMLRPCSequenceDB, BlastDBXMLRPC),
                           (BlastDB, XMLRPCSequenceDB, BlastDBXMLRPC),
                           (AnnotationDB, AnnotationClient, AnnotationServer)]
            try:
                from cnestedlist import NLMSA
                from xnestedlist import NLMSAClient, NLMSAServer
                serverClasses.append((NLMSA, NLMSAClient, NLMSAServer))
            except ImportError: # cnestedlist NOT INSTALLED, SO SKIP...
                pass
        if clientHost is None: # DEFAULT: USE THE SAME HOST STRING AS SERVER
            clientHost = self.host
        clientDict = {}
        for id, obj in resourceDict.items():
            # Save all objects matching serverClasses.
            skipThis = False
            for skipClass in excludeClasses: # CHECK LIST OF CLASSES TO EXCLUDE
                if isinstance(obj, skipClass):
                    skipThis = True
                    break
            if skipThis:
                continue # DO NOT INCLUDE THIS OBJECT IN SERVER
            skipThis = True
            for baseKlass, clientKlass, serverKlass in serverClasses:
                if isinstance(obj, baseKlass) and not isinstance(obj,
                                                                 clientKlass):
                    skipThis = False # OK, WE CAN SERVE THIS CLASS
                    break
            if skipThis: # HAS NO XMLRPC CLIENT-SERVER CLASS PAIRING
                try: # SAVE IT AS ITSELF
                    self.client_dict_setitem(clientDict, id, obj,
                                             badClasses=nonPortableClasses)
                except WorldbaseNotPortableError:
                    pass # HAS NON-PORTABLE LOCAL DEPENDENCIES, SO SKIP IT
                continue # GO ON TO THE NEXT DATA RESOURCE
            try: # TEST WHETHER obj CAN BE RE-CLASSED TO CLIENT / SERVER
                # Convert to server class for serving.`
                obj.__class__ = serverKlass
            except TypeError: # GRR, EXTENSION CLASS CAN'T BE RE-CLASSED...
                state = obj.__getstate__() # READ obj STATE
                newobj = serverKlass.__new__(serverKlass) # ALLOCATE NEW OBJECT
                newobj.__setstate__(state) # AND INITIALIZE ITS STATE
                obj = newobj # THIS IS OUR RE-CLASSED VERSION OF obj
            try: # USE OBJECT METHOD TO SAVE HOST INFO, IF ANY...
                obj.saveHostInfo(clientHost, self.port, id)
            except AttributeError: # TRY TO SAVE URL AND NAME DIRECTLY ON obj
                obj.url = 'http://%s:%d' % (clientHost, self.port)
                obj.name = id
            obj.__class__ = clientKlass # CONVERT TO CLIENT CLASS FOR PICKLING
            self.client_dict_setitem(clientDict, id, obj)
            obj.__class__ = serverKlass # CONVERT TO SERVER CLASS FOR SERVING
            self[id] = obj # ADD TO XMLRPC SERVER
        self.registrationData = clientDict # SAVE DATA FOR SERVER REGISTRATION
        if withIndex: # SERVE OUR OWN INDEX AS A STATIC, READ-ONLY INDEX
            myIndex = MetabaseServer(name, readOnly=True, # CREATE EMPTY INDEX
                                     downloadDB=downloadDB)
            self['index'] = myIndex # ADD TO OUR XMLRPC SERVER
            # Add our resources to the index.
            self.register('', '', server=myIndex)

    def client_dict_setitem(self, clientDict, k, obj, **kwargs):
        'save pickle and schema for obj into clientDict'
        pickleString = dumps(obj, **kwargs) # PICKLE THE CLIENT OBJECT, SAVE
        clientDict[k] = (get_info_dict(obj, pickleString), pickleString)
        try: # SAVE SCHEMA INFO AS WELL...
            clientDict['SCHEMA.' + k] = (dict(schema_version='1.0'),
                                         self.mdb.getschema(k))
        except KeyError:
            pass # NO SCHEMA FOR THIS OBJ, SO NOTHING TO DO


class ResourcePath(object):
    'simple way to read resource names as python foo.bar.bob expressions'

    def __init__(self, mdb, base=None):
        self.__dict__['_path'] = base # AVOID TRIGGERING setattr!
        self.__dict__['_mdb'] = mdb

    def getPath(self, name):
        if self._path is not None:
            return self._path + '.' + name
        else:
            return name

    def __getattr__(self, name):
        'extend the resource path by one more attribute'
        attr = self._pathClass(self._mdb, self.getPath(name))
        # MUST NOT USE setattr BECAUSE WE OVERRIDE THIS BELOW!
        self.__dict__[name] = attr # CACHE THIS ATTRIBUTE ON THE OBJECT
        return attr

    def __call__(self, *args, **kwargs):
        'construct the requested resource'
        return self._mdb(self._path, *args, **kwargs)

    def __setattr__(self, name, obj):
        'save obj using the specified resource name'
        self._mdb.add_resource(self.getPath(name), obj)

    def __delattr__(self, name):
        self._mdb.delete_resource(self.getPath(name))
        try: # IF ACTUAL ATTRIBUTE EXISTS, JUST DELETE IT
            del self.__dict__[name]
        except KeyError: # TRY TO DELETE RESOURCE FROM THE DATABASE
            pass # NOTHING TO DO

    def __dir__(self, prefix=None, start=None):
        """return list of our attributes from worldbase search"""
        if prefix is None:
            start = len(self._path) + 1 # skip past . separator
            prefix = self._path
        l = self._mdb.dir(prefix)
        d = {}
        for name in l:
            if name.startswith(prefix):
                d[name[start:].split('.')[0]] = None
        return d.keys()

ResourcePath._pathClass = ResourcePath


class ResourceRoot(ResourcePath):
    'provide proxy to public metabase methods'

    def __init__(self, mdb, base=None, zones=None):
        ResourcePath.__init__(self, mdb, base)
        self.__dict__['schema'] = mdb.Schema # AVOID TRIGGERING setattr!
        if zones is not None:
            self.__dict__['zones'] = zones
        for attr in ('dir', 'commit', 'rollback', 'add_resource',
                     'delete_resource', 'clear_cache', 'add_schema',
                     'update', 'list_pending'):
            self.__dict__[attr] = getattr(mdb, attr) # mirror metabase methods

    def __call__(self, resID, *args, **kwargs):
        """Construct the requested resource"""
        return self._mdb(resID, *args, **kwargs)

    def __dir__(self):
        return ResourcePath.__dir__(self, '', 0)


class ResourceZone(object):
    'provide pygr.Data old-style interface to resource zones'

    def __init__(self, mdb, zoneName):
        self._mdbParent = mdb
        self._zoneName = zoneName

    def __getattr__(self, name):
        # Make sure metabases have been loaded.
        self._mdbParent.update(keepCurrentPath=True)
        try:
            mdb = self._mdbParent.zoneDict[self._zoneName] # get our zone
        except KeyError:
            raise ValueError('no zone "%s" available' % self._zoneName)
        if name == 'schema': # get schema root
            return SchemaPath.__getitem__(self, mdb)
        else: # treat as regular worldbase string
            return ResourcePath.__getitem__(self, mdb, name)


class SchemaPath(ResourcePath):
    'save schema information for a resource'

    def __setattr__(self, name, schema):
        try:
            schema.saveSchema # VERIFY THAT THIS LOOKS LIKE A SCHEMA OBJECT
        except AttributeError:
            raise ValueError('not a valid schema object!')
        self._mdb.queue_schema_obj(self, name, schema) # QUEUE IT

    def __delattr__(self, attr):
        raise NotImplementedError('schema deletion is not yet implemented.')

SchemaPath._pathClass = SchemaPath


class DirectRelation(object):
    'bind an attribute to the target'

    def __init__(self, target):
        self.targetID = getID(target)

    def schemaDict(self):
        return dict(targetID=self.targetID)

    def saveSchema(self, source, attr, mdb, **kwargs):
        d = self.schemaDict()
        d.update(kwargs) # ADD USER-SUPPLIED ARGS
        try: # IF kwargs SUPPLIED A TARGET, SAVE ITS ID
            d['targetID'] = getID(d['targetDB'])
            del d['targetDB']
        except KeyError:
            pass
        mdb.saveSchema(getID(source), attr, d)


class ItemRelation(DirectRelation):
    'bind item attribute to the target'

    def schemaDict(self):
        return dict(targetID=self.targetID, itemRule=True)


class ManyToManyRelation(object):
    'a general graph mapping from sourceDB -> targetDB with edge info'
    _relationCode = 'many:many'

    def __init__(self, sourceDB, targetDB, edgeDB=None, bindAttrs=None,
                 sourceNotNone=None, targetNotNone=None):
        self.sourceDB = getID(sourceDB) # CONVERT TO STRING RESOURCE ID
        self.targetDB = getID(targetDB)
        if edgeDB is not None:
            self.edgeDB = getID(edgeDB)
        else:
            self.edgeDB = None
        self.bindAttrs = bindAttrs
        if sourceNotNone is not None:
            self.sourceNotNone = sourceNotNone
        if targetNotNone is not None:
            self.targetNotNone = targetNotNone

    def save_graph_bindings(self, graphDB, attr, mdb):
        '''save standard schema bindings to graphDB attributes
        sourceDB, targetDB, edgeDB'''
        graphDB = graphDB.getPath(attr) # GET STRING ID FOR source
        self.name = graphDB
        mdb.saveSchemaEdge(self) #SAVE THIS RULE
        b = DirectRelation(self.sourceDB) # SAVE sourceDB BINDING
        b.saveSchema(graphDB, 'sourceDB', mdb)
        b = DirectRelation(self.targetDB) # SAVE targetDB BINDING
        b.saveSchema(graphDB, 'targetDB', mdb)
        if self.edgeDB is not None: # SAVE edgeDB BINDING
            b = DirectRelation(self.edgeDB)
            b.saveSchema(graphDB, 'edgeDB', mdb)
        return graphDB

    def saveSchema(self, path, attr, mdb):
        'save schema bindings associated with this rule'
        graphDB = self.save_graph_bindings(path, attr, mdb)
        if self.bindAttrs is not None:
            bindObj = (self.sourceDB, self.targetDB, self.edgeDB)
            bindArgs = [{}, dict(invert=True), dict(getEdges=True)]
            try: # USE CUSTOM INVERSE SCHEMA IF PROVIDED BY TARGET DB
                bindArgs[1] = mdb.get_pending_or_find(graphDB). \
                        _inverse_schema()
            except AttributeError:
                pass
            for i in range(3):
                if len(self.bindAttrs) > i and self.bindAttrs[i] is not None:
                    b = ItemRelation(graphDB) # SAVE ITEM BINDING
                    b.saveSchema(bindObj[i], self.bindAttrs[i],
                                 mdb, **bindArgs[i])

    def delschema(self, resourceDB):
        'delete resource attribute bindings associated with this rule'
        if self.bindAttrs is not None:
            bindObj = (self.sourceDB, self.targetDB, self.edgeDB)
            for i in range(3):
                if len(self.bindAttrs) > i and self.bindAttrs[i] is not None:
                    resourceDB.delschema(bindObj[i], self.bindAttrs[i])


class OneToManyRelation(ManyToManyRelation):
    _relationCode = 'one:many'


class OneToOneRelation(ManyToManyRelation):
    _relationCode = 'one:one'


class ManyToOneRelation(ManyToManyRelation):
    _relationCode = 'many:one'


class InverseRelation(DirectRelation):
    "bind source and target as each other's inverse mappings"
    _relationCode = 'inverse'

    def saveSchema(self, source, attr, mdb, **kwargs):
        'save schema bindings associated with this rule'
        source = source.getPath(attr) # GET STRING ID FOR source
        self.name = source
        mdb.saveSchemaEdge(self) #SAVE THIS RULE
        DirectRelation.saveSchema(self, source, 'inverseDB',
                                  mdb, **kwargs) # source -> target
        b = DirectRelation(source) # CREATE REVERSE MAPPING
        b.saveSchema(self.targetID, 'inverseDB',
                     mdb, **kwargs) # target -> source

    def delschema(self, resourceDB):
        resourceDB.delschema(self.targetID, 'inverseDB')


def getID(obj):
    'get persistent ID of the object or raise AttributeError'
    if isinstance(obj, str): # TREAT ANY STRING AS A RESOURCE ID
        return obj
    elif isinstance(obj, ResourcePath):
        return obj._path # GET RESOURCE ID FROM A ResourcePath
    else:
        try: # GET RESOURCE'S PERSISTENT ID
            return obj._persistent_id
        except AttributeError:
            raise AttributeError('this obj has no persistent ID!')

########NEW FILE########
__FILENAME__ = nlmsa_utils
import os
import types
import classutil
import logger
from UserDict import DictMixin


class NLMSASeqList(list):

    def __init__(self, nlmsaSeqDict):
        list.__init__(self)
        self.nlmsaSeqDict = nlmsaSeqDict

    def __getitem__(self, nlmsaID):
        'return NLMSASequence for a given nlmsa_id'
        try:
            return list.__getitem__(self, nlmsaID)
        except IndexError:
            seqID, nsID = self.nlmsaSeqDict.IDdict[str(nlmsaID)]
            return list.__getitem__(self, nsID)

    def getSeq(self, nlmsaID):
        'return seq for a given nlmsa_id'
        seqID, nsID = self.nlmsaSeqDict.IDdict[str(nlmsaID)]
        return self.nlmsaSeqDict.nlmsa.seqDict[seqID]

    def getSeqID(self, nlmsaID):
        'return seqID for a given nlmsa_id'
        seqID, nsID = self.nlmsaSeqDict.IDdict[str(nlmsaID)]
        return seqID

    def is_lpo(self, id):
        if id >= len(self):
            return False
        ns = self[id]
        if ns.is_lpo:
            return True
        else:
            return False

    def nextID(self):
        return len(self)


class EmptySliceError(KeyError):
    pass


class EmptyAlignmentError(ValueError):
    pass


class EmptySlice:
    'Empty slice for use by NLMSASlice'

    def __init__(self, seq):
        self.seq = seq

    def edges(self, *args, **kwargs):
        return []

    def items(self, **kwargs):
        return []

    def iteritems(self, **kwargs):
        return iter([])

    def keys(self, **kwargs):
        return []

    def __iter__(self):
        return iter([])

    def __getitem__(self, k):
        raise KeyError

    def __len__(self):
        return 0

    def matchIntervals(self, seq=None):
        return []

    def findSeqEnds(self, seq):
        raise KeyError('seq not aligned in this interval')

    def generateSeqEnds(self):
        return []

    def groupByIntervals(self, **kwargs):
        return {}

    def groupBySequences(self, **kwargs):
        return []

    def split(self, **kwargs):
        return []

    def regions(self, **kwargs):
        return []

    def __cmp__(self, other):
        return cmp(self.seq, other.seq)

    def rawIvals(self):
        return []


class _NLMSASeqDict_ValueWrapper(object):
    """A wrapper class for NLMSASeqDict to use to store 3-tuples in its cache.

    NLMSASeqDict has a most-recent-values cache containing (id,
    seqlist, offset) tuples for each referenced pathForward.  However,
    tuples cannot be stored in a weakref dictionary.  This class provides
    a tuple-like wrapper object that *can* be stored in a weakref dict.
    
    """
    def __init__(self, nlmsaID, seqlist, offset):
        self.v = (nlmsaID, seqlist, offset)

    def __hash__(self):
        return hash(self.v)

    def __len__(self):
        return 3

    def __getitem__(self, n):
        return self.v[n]

_DEFAULT_SEQUENCE_CACHE_SIZE=100
class NLMSASeqDict(object, DictMixin):
    """Index sequences by pathForward, and use list to keep reverse mapping.

    Keeps a cache of n most recently accessed sequences, up to
    maxSequenceCacheSize (defaults to 100).
    
    """

    def __init__(self, nlmsa, filename, mode, idDictClass=None,
                 maxSequenceCacheSize=_DEFAULT_SEQUENCE_CACHE_SIZE):
        self._cache = classutil.RecentValueDictionary(maxSequenceCacheSize)
        self.seqlist = NLMSASeqList(self)
        self.nlmsa = nlmsa
        self.filename = filename
        if mode == 'memory': # just use python dictionary
            idDictClass = dict
        elif mode == 'w': # new database
            mode = 'n'
        if idDictClass is None: # use persistent id dictionary storage
            self.seqIDdict = classutil.open_shelve(filename + '.seqIDdict',
                                                   mode)
            self.IDdict = classutil.open_shelve(filename + '.idDict', mode)
        else: # user supplied class for id dictionary storage
            self.seqIDdict = idDictClass()
            self.IDdict = idDictClass()

    def saveSeq(self, seq, nsID= -1, offset=0, nlmsaID=None):
        'save mapping of seq to specified (nlmsaID,ns,offset)'
        if nsID < 0: # let the union figure it out
            self.nlmsa.currentUnion.__iadd__(seq)
            return # the union added it for us, no need to do anything
        if isinstance(seq, types.StringType):
            id = seq # treat this as fully qualified identifier
        else: # get the identfier from the seq / database
            id = self.getSeqID(seq)
        if nlmsaID is None: # allocate a new unique id
            nlmsaID = self.nlmsa.nextID()
        self.seqIDdict[id] = nlmsaID, nsID, offset
        self.IDdict[str(nlmsaID)] = id, nsID

    def getIDcoords(self, seq):
        'return nlmsaID,start,stop for a given seq ival.'
        nlmsaID = self.getID(seq)
        return nlmsaID, seq.start, seq.stop # standard coords

    def getID(self, seq):
        'return nlmsa_id for a given seq'
        return self[seq][0]

    def __getitem__(self, seq):
        'return nlmsaID,NLMSASequence,offset for a given seq'
        if not hasattr(seq, 'annotationType'): # don't cache annotations
            try: # look in our sequence cache
                return self._cache[seq.pathForward]
            except AttributeError:
                raise KeyError('key must be a sequence interval!')
            except KeyError:
                pass
        seqID = self.getSeqID(seq) # use seq id to look up...
        try:
            nlmsaID, nsID, offset = self.seqIDdict[seqID]
        except KeyError:
            raise KeyError('seq not found in this alignment')
        v = nlmsaID, self.seqlist[nsID], offset
        if not hasattr(seq, 'annotationType'): # don't cache annotations
            self._cache[seq.pathForward] = _NLMSASeqDict_ValueWrapper(*v)
        return v

    def __iter__(self):
        'iterate over sequences in this alignment'
        for seqID in self.seqIDdict:
            yield self.nlmsa.seqDict[seqID]

    def getSeqID(self, seq):
        'return fully qualified sequence ID for this seq'
        return (~(self.nlmsa.seqDict))[seq]

    def __setitem__(self, k, ns):
        'save mapping of seq to the specified NLMSASequence'
        self.seqlist.append(ns)
        if isinstance(k, types.StringType):
            # Allow build with a string object.
            self._cache[k] = (ns.id, ns, 0)
        elif k is not None:
            self._cache[k.pathForward] = (ns.id, ns, 0)

    def __iadd__(self, ns):
        'add coord system ns to the alignment'
        self[None] = ns
        return self # iadd must return self!!!

    def close(self):
        'finalize and close shelve indexes'
        try:
            do_close = self.seqIDdict.close
        except AttributeError:
            return # our storage doesn't support close(), so nothing to do
        do_close() # close both shelve objects
        self.IDdict.close()

    def reopenReadOnly(self, mode='r'):
        'save existing data and reopen in read-only mode'
        self.close()
        self.seqIDdict = classutil.open_shelve(self.filename + '.seqIDdict',
                                               mode)
        self.IDdict = classutil.open_shelve(self.filename + '.idDict', mode)

    def getUnionSlice(self, seq):
        'get union coords for this seq interval, adding seq to index if needed'
        try:
            id, ns, offset = self[seq] # look up in index
        except KeyError:
            self.saveSeq(seq) # add this new sequence to our current union
            id, ns, offset = self[seq] # look up in index
        # Make sure to handle annotations right
        i, start, stop = self.getIDcoords(seq)
        if start < 0: # reverse orientation
            return ns, slice(start - offset, stop - offset) # use union coords
        else: # forward orientation
            return ns, slice(start + offset, stop + offset) # use union coords

    def clear_cache(self):
        'Clear the cache of saved sequences.'
        self._cache.clear()


def splitLPOintervals(lpoList, ival, targetIval=None):
    'return list of intervals split to different LPOs'
    if ival.start < 0: # reverse orientation: force into forward ori
        start= -(ival.stop)
        stop= -(ival.start)
    else: # forward orientation
        start=ival.start
        stop=ival.stop
    l = []
    i = len(lpoList) - 1
    while i >= 0:
        offset = lpoList[i].offset
        if offset < stop: # appears to be in this
            if offset <= start: # fits completely in this LPO
                if ival.start < 0: # reverse ori
                    myslice = slice(offset - stop, offset - start)
                else: # forward ori
                    myslice = slice(start - offset, stop - offset)
                if targetIval is not None:
                    l.append((lpoList[i], myslice, targetIval))
                else:
                    l.append((lpoList[i], myslice))
                return l # done
            else: # continues past start of this LPO
                if ival.start < 0: # reverse ori
                    myslice = slice(offset - stop, 0)
                else: # forward ori
                    myslice = slice(0, stop - offset)
                if targetIval is not None:
                    l.append((lpoList[i], myslice, targetIval[offset
                                                              - start:]))
                    # Remove the already-appended part
                    targetIval = targetIval[:offset - start]
                else:
                    l.append((lpoList[i], myslice))
                stop = offset
        i -= 1 # continue to previous LPO
    raise ValueError('empty lpoList or offset not starting at 0?  Debug!')


class BuildMSASlice(object):

    def __init__(self, ns, start, stop, id, offset, is_lpo=0, seq=None):
        self.ns = ns
        self.start = start
        self.stop = stop
        self.id = id
        self.offset = offset
        self.is_lpo = is_lpo
        self.seq = seq

    def offsetSlice(self, ival):
        if ival.orientation < 0:
            return slice(ival.start - self.offset, ival.stop - self.offset)
        else:
            return slice(ival.start + self.offset, ival.stop + self.offset)

    def __iadd__(self, targetIval):
        'save an alignment edge between self and targetIval'
        if self.is_lpo: # assign to correct LPO(s)
            if isinstance(targetIval, types.SliceType):
                raise ValueError('you attempted to map LPO --> LPO?!?')
            self.ns.nlmsaLetters.__iadd__(targetIval)
            splitList = splitLPOintervals(self.ns.nlmsaLetters.lpoList,
                                          slice(self.start, self.stop),
                                          targetIval)
            for ns, src, target in splitList:
                # Save intervals to respective LPOs; LPO --> target
                ns[src] = self.ns.nlmsaLetters.seqs.getIDcoords(target)
                if self.ns.nlmsaLetters.is_bidirectional:
                    nsu, myslice = self.ns.nlmsaLetters.seqs \
                            .getUnionSlice(target)
                    # Save target --> LPO
                    nsu[myslice] = (ns.id, src.start, src.stop)
        else:
            if isinstance(targetIval, types.SliceType): # target is LPO
                splitList = splitLPOintervals(self.ns.nlmsaLetters.lpoList,
                                            targetIval, self.seq)
                for ns, target, src in splitList:
                    self.ns[self.offsetSlice(src)] = (ns.id, target.start,
                                                      target.stop)
                    if self.ns.nlmsaLetters.is_bidirectional:
                        # Save LPO --> SRC
                        ns[target]=(self.id, src.start, src.stop)
            else: # both src and target are normal seqs.  use_virtual_lpo!!
                self.ns.nlmsaLetters.__iadd__(targetIval)
                self.ns.nlmsaLetters.init_pairwise_mode()
                # Our virtual LPO
                ns_lpo = self.ns.nlmsaLetters.seqlist[self.ns.id - 1]
                # Save src --> target
                ns_lpo[self.offsetSlice(self.seq)] = self.ns.nlmsaLetters \
                        .seqs.getIDcoords(targetIval)
                if self.ns.nlmsaLetters.is_bidirectional:
                    nsu, myslice = self.ns.nlmsaLetters.seqs \
                            .getUnionSlice(targetIval)
                    # Our virtual LPO
                    ns_lpo = self.ns.nlmsaLetters.seqlist[nsu.id - 1]
                    # Save target --> src
                    ns_lpo[myslice] = (self.id, self.start, self.stop)
        return self # iadd must always return self

    def __setitem__(self, k, v):
        if v is not None:
            raise ValueError('NLMSA cannot save edge-info. Only \
                             nlmsa[s1][s2]=None allowed')
        self += k


def read_seq_dict(pathstem, trypath=None):
    'read seqDict for NLMSA'
    if os.access(pathstem + '.seqDictP', os.R_OK):
        from pygr import worldbase
        ifile = file(pathstem+'.seqDictP', 'rb') # pickle is binary file!
        try: # load from worldbase-aware pickle file
            seqDict = worldbase._mdb.loads(ifile.read())
        finally:
            ifile.close()
    elif os.access(pathstem + '.seqDict', os.R_OK): # old-style union header
        import seqdb
        seqDict = seqdb.PrefixUnionDict(filename=pathstem+'.seqDict',
                                        trypath=trypath)
    else:
        raise ValueError('''Unable to find seqDict file
%s.seqDictP or %s.seqDict
and no seqDict provided as an argument''' % (pathstem, pathstem))
    return seqDict


def save_seq_dict(pathstem, seqDict):
    'save seqDict to a worldbase-aware pickle file'
    from metabase import dumps
    ofile = file(pathstem + '.seqDictP', 'wb') # pickle is binary file!
    try:
        ofile.write(dumps(seqDict))
    finally:
        ofile.close()


def prune_self_mappings(src_prefix, dest_prefix, is_bidirectional):
    '''return is_bidirectional flag according to whether source and
    target are the same genome.  This handles axtNet reading, in which
    mappings between genomes are given in only one direction, whereas
    mappings between the same genome are given in both directions.'''
    if src_prefix == dest_prefix:
        return 0
    else:
        return 1


def nlmsa_textdump_unpickler(filepath, kwargs):
    from cnestedlist import textfile_to_binaries, NLMSA
    logger.info('Saving NLMSA indexes from textdump: %s' % filepath)
    try:
        buildpath = os.environ['WORLDBASEBUILDDIR']
    except KeyError:
        buildpath = classutil.get_env_or_cwd('PYGRDATABUILDDIR')
    path = textfile_to_binaries(filepath, buildpath=buildpath, **kwargs)
    o = NLMSA(path) # now open in read mode from the saved index fileset
    o._saveLocalBuild = True # mark this for saving in local metabase
    return o


nlmsa_textdump_unpickler.__safe_for_unpickling__ = 1


class NLMSABuilder(object):
    'when unpickled triggers construction of NLMSA from textdump'
    _worldbase_no_cache = True # force worldbase to reload this fresh

    def __init__(self, filepath, **kwargs):
        self.filepath = filepath
        self.kwargs = kwargs

    def __reduce__(self):
        return (nlmsa_textdump_unpickler, (self.filepath, self.kwargs))


class SeqCacheOwner(object):
    'weak referenceable object: workaround for pyrex extension classes'

    def __init__(self):
        self.cachedSeqs = {}

    def cache_reference(self, seq):
        'keep a ref to seqs cached on our behalf'
        self.cachedSeqs[seq.id] = seq


def generate_nlmsa_edges(self, *args, **kwargs):
    """iterate over all edges for all sequences in the alignment.
    Very slow for a big alignment!"""
    for seq in self.seqs:
        myslice = self[seq]
        for results in myslice.edges(*args, **kwargs):
            yield results


def get_interval(seq, start, end, ori):
    "trivial function to get the interval seq[start:end] with requested ori"
    if ori < 0:
        return seq.absolute_slice(-end, -start)
    else:
        return seq.absolute_slice(start, end)


_default_ivals_attrs = dict(idDest='id', startDest='start',
                            stopDest='stop', oriDest='ori')


class CoordsToIntervals(object):
    '''Transforms coord objects to (ival1,ival2) aligned interval pairs.

    The intervals can come in in two forms:
    First, as a list, with [src, dest1, dest2, dest3] information;
    or second, as an object, with attributes specifying src/dest info.
    '''

    def __init__(self, srcDB, destDB=None,
                 alignedIvalsAttrs=_default_ivals_attrs):
        self.srcDB = srcDB
        if destDB:
            self.destDB = destDB
        else:
            self.destDB = srcDB
        self.getAttr = classutil.make_attribute_interface(alignedIvalsAttrs)

    def __call__(self, alignedCoords):
        '''Read interval info from alignedCoords and generate actual intervals.

        Information read is id, start, stop, and orientation (ori).
        '''
        for c in alignedCoords:
            if isinstance(c, (CoordsGroupStart, CoordsGroupEnd)):
                yield c # just pass grouping-info through
                continue

            try:
                srcData = c[0] # align everything to the first interval
                destSet = c[1:]
            except TypeError:
                srcData = c # extract both src and dest from ivals object
                destSet = [c]

            id = self.getAttr(srcData, 'id')
            start = self.getAttr(srcData, 'start')
            stop = self.getAttr(srcData, 'stop')
            ori = self.getAttr(srcData, 'ori', 1)    # default orientation: +

            srcIval = get_interval(self.srcDB[id], start, stop, ori)

            # get the dest interval(s) and yield w/src.
            for destData in destSet:
                idDest = self.getAttr(destData, 'idDest')
                startDest = self.getAttr(destData, 'startDest')
                stopDest = self.getAttr(destData, 'stopDest')
                oriDest = self.getAttr(destData, 'oriDest', 1) # default ori: +

                destIval = get_interval(self.destDB[idDest], startDest,
                                        stopDest, oriDest)

                yield srcIval, destIval # generate aligned intervals


def add_aligned_intervals(al, alignedIvals):
    '''Save a set of aligned intervals to alignment.
    '''
    # for each pair of aligned intervals, save them into the alignment.
    for t in alignedIvals:
        # is 't' a marker object for start or end of a group of coordinates?
        if isinstance(t, (CoordsGroupStart, CoordsGroupEnd)):
            continue # ignore grouping markers

        (src, dest) = t
        al += src
        al[src][dest] = None                # save their alignment


class CoordsGroupStart(object):
    '''Marker object indicating start of a coordinates group.

    See BlastHitParser for an example.'''
    pass


class CoordsGroupEnd(object):
    '''Marker object indicating end of a group of coordinates.

    See BlastHitParser for an example.'''
    pass

########NEW FILE########
__FILENAME__ = parse_blast
from __future__ import generators
import math
from nlmsa_utils import CoordsGroupStart, CoordsGroupEnd

# AUTHORS: zfierstadt, leec


def is_line_start(token, line):
    "check whether line begins with token"
    return token == line[:len(token)]


def get_ori_letterunit(start, end, seq, gapchar='-'):
    """try to determine orientation (1 or -1) based on whether start>end,
    and letterunit (1 or 3) depending on the ratio of end-start difference
    vs the actual non-gap letter count.  Returns tuple (ori,letterunit)"""
    if end > start:
        ori = 1
    else:
        ori = -1
    ngap = 0
    for l in seq:
        if l == gapchar:
            ngap += 1
    seqlen = len(seq) - ngap
    if ori * float(end - start) / seqlen > 2.0:
        letterunit = 3
    else:
        letterunit = 1
    return ori, letterunit


class BlastIval(object):

    def __repr__(self):
        return '<BLAST-IVAL: ' + repr(self.__dict__) + '>'


class BlastHitParser(object):
    """reads alignment info from blastall standard output.
    Method parse_file(fo) reads file object fo, and generates tuples
    suitable for BlastIval."""
    gapchar = '-'

    def __init__(self):
        self.hit_id = 0
        self.nline = 0
        self.reset()

    def reset(self):
        "flush any alignment info, so we can start reading new alignment"
        self.query_seq = ""
        self.subject_seq = ""
        self.hit_id += 1

    def save_query(self, line):
        self.query_id = line.split()[1]

    def save_subject(self, line):
        self.subject_id = line.split()[0][1:]

    def save_score(self, line):
        "save a Score: line"
        self.blast_score = float(line.split()[2])
        s = line.split()[7]
        if s[0] == 'e':
            s = '1' + s
        try:
            self.e_value = -math.log(float(s)) / math.log(10.0)
        except (ValueError, OverflowError):
            self.e_value = 300.

    def save_identity(self, line):
        "save Identities line"
        s = line.split()[3][1:]
        self.identity_percent = int(s[:s.find('%')])

    def save_query_line(self, line):
        "save a Query: line"
        c=line.split()
        self.query_end=int(c[3])
        if not self.query_seq:
            self.query_start=int(c[1])
            # Handle forward orientation.
            if self.query_start < self.query_end:
                self.query_start -= 1
        self.query_seq+=c[2]
        self.seq_start_char=line.find(c[2], 5) # IN CASE BLAST SCREWS UP Sbjct:

    def save_subject_line(self, line):
        "save a Sbjct: line, attempt to handle various BLAST insanities"
        c=line.split()
        if len(c)<4: # OOPS, BLAST FORGOT TO PUT SPACE BEFORE 1ST NUMBER
            # THIS HAPPENS IN TBLASTN... WHEN THE SUBJECT SEQUENCE
            # COVERS RANGE 1-1200, THE FOUR DIGIT NUMBER WILL RUN INTO
            # THE SEQUENCE, WITH NO SPACE!!
            c = ['Sbjct:', line[6:self.seq_start_char]] \
               + line[self.seq_start_char:].split() # FIX BLAST SCREW-UP
        self.subject_end=int(c[3])
        if not self.subject_seq:
            self.subject_start = int(c[1])
            # Handle forward orientation.
            if self.subject_start < self.subject_end:
                self.subject_start -= 1
        self.subject_seq += c[2]
        lendiff = len(self.query_seq) - len(self.subject_seq)
        if lendiff > 0: # HANDLE TBLASTN SCREWINESS: Sbjct SEQ OFTEN TOO SHORT!
            # THIS APPEARS TO BE ASSOCIATED ESPECIALLY WITH STOP CODONS *
            self.subject_seq += lendiff * 'A' # EXTEND TO SAME LENGTH AS QUERY
        elif lendiff < 0 and not hasattr(self, 'ignore_query_truncation'):
            # WHAT THE HECK?!?!  WARN THE USER: BLAST RESULTS ARE SCREWY...
            raise ValueError(
                """BLAST appears to have truncated the Query: sequence
                to be shorter than the Sbjct: sequence:
                Query: %s
                Sbjct: %s
                This should not happen!  To ignore this error, please
                create an attribute ignore_query_truncation on the
                BlastHitParser object.""" % (self.query_seq, self.subject_seq))

    def get_interval_obj(self, q_start, q_end, s_start, s_end,
                         query_ori, query_factor, subject_ori, subject_factor):
        "return interval result as an object with attributes"
        o = BlastIval()
        o.hit_id = self.hit_id
        o.src_id = self.query_id
        o.dest_id = self.subject_id
        o.blast_score = self.blast_score
        o.e_value = self.e_value
        o.percent_id = self.identity_percent
        o.src_ori = query_ori
        o.dest_ori = subject_ori
        query_start = self.query_start+q_start*query_ori*query_factor
        query_end = self.query_start+q_end*query_ori*query_factor
        subject_start = self.subject_start+s_start*subject_ori*subject_factor
        subject_end = self.subject_start+s_end*subject_ori*subject_factor
        if query_start<query_end:
            o.src_start = query_start
            o.src_end = query_end
        else:
            o.src_start = query_end
            o.src_end = query_start
        if subject_start<subject_end:
            o.dest_start = subject_start
            o.dest_end = subject_end
        else:
            o.dest_start = subject_end
            o.dest_end = subject_start
        return o

    def is_valid_hit(self):
        return self.query_seq and self.subject_seq

    def generate_intervals(self):
        "generate interval tuples for the current alignment"
        yield CoordsGroupStart() # bracket with grouping markers

        query_ori, query_factor = get_ori_letterunit(self.query_start,\
                  self.query_end, self.query_seq, self.gapchar)
        subject_ori, subject_factor = get_ori_letterunit(self.subject_start,\
                  self.subject_end, self.subject_seq, self.gapchar)
        q_start= -1
        s_start= -1
        i_query=0
        i_subject=0
        for i in range(len(self.query_seq)): # SCAN ALIGNMENT FOR GAPS
            if self.query_seq[i] == self.gapchar or \
               self.subject_seq[i] == self.gapchar:
                if q_start >= 0: # END OF AN UNGAPPED INTERVAL
                    yield self.get_interval_obj(q_start, i_query,
                                                s_start, i_subject,
                                                query_ori, query_factor,
                                                subject_ori, subject_factor)
                q_start= -1
            elif q_start<0: # START OF AN UNGAPPED INTERVAL
                q_start=i_query
                s_start=i_subject
            if self.query_seq[i]!=self.gapchar: # COUNT QUERY LETTERS
                i_query+=1
            if self.subject_seq[i]!=self.gapchar: # COUNT SUBJECT LETTERS
                i_subject+=1
        if q_start>=0: # REPORT THE LAST INTERVAL
            yield self.get_interval_obj(q_start, i_query,
                                        s_start, i_subject,
                                        query_ori, query_factor,
                                        subject_ori, subject_factor)

        yield CoordsGroupEnd()

    def parse_file(self, myfile):
        "generate interval tuples by parsing BLAST output from myfile"
        for line in myfile:
            self.nline += 1
            if self.is_valid_hit() and \
               (is_line_start('>', line) or is_line_start(' Score =', line) \
                or is_line_start('  Database:', line) \
                or is_line_start('Query=', line)):
                for t in self.generate_intervals(): # REPORT THIS ALIGNMENT
                    yield t # GENERATE ALL ITS INTERVAL MATCHES
                self.reset() # RESET TO START A NEW ALIGNMENT
            if is_line_start('Query=', line):
                self.save_query(line)
            elif is_line_start('>', line):
                self.save_subject(line)
            elif is_line_start(' Score =', line):
                self.save_score(line)
            elif 'Identities =' in line:
                self.save_identity(line)
            elif is_line_start('Query:', line):
                self.save_query_line(line)
            elif is_line_start('Sbjct:', line):
                self.save_subject_line(line)
        if self.nline == 0: # no blast output??
            raise IOError('No BLAST output. Check that blastall is \
                          in your PATH')

if __name__=='__main__':
    import sys
    p=BlastHitParser()
    for t in p.parse_file(sys.stdin):
        print t

########NEW FILE########
__FILENAME__ = schema

import types


# STORES DICTIONARY OF ATTRIBUTE-BOUND GRAPHS
# AND LIST OF UNBOUND GRAPHS
class SchemaDict(dict):
    """Container for schema rules bound to a class or object. Rules
    are stored in two indexes for fast access, indexed by graph, and
    indexed by attrname. Use += and -= to add or remove rules.
    """

    def __init__(self, newlist=(), baselist=()):
        "Initialize schema list from list of base classes and newlist of rules"
        self.attrs = {}
        dict.__init__(self)
        # COMBINE SCHEMAS FROM PARENTS WITH NEW SCHEMA LIST
        for b in baselist:
            if hasattr(b, '__class_schema__'):
                self.update(b.__class_schema__)
                self.attrs.update(b.__class_schema__.attrs)
        for i in newlist: # newlist OVERRIDES OLD DEFS FROM baselist
            self += i

    def __iadd__(self, i):
        "Add a schema rule to this SchemaDict"
        g = i[0]
        if len(i) >= 2:
            if isinstance(i[1], types.StringType):
                if i[1] in self.attrs: # REMOVE OLD ENTRY
                    self -= self.attrs[i[1]]
                self.attrs[i[1]] = i # SAVE IN INDEX ACCORDING TO ATTR NAME
            else:
                raise TypeError('Attribute name must be a string')
        if g not in self:
            self[g] = []
        self[g].append(i) # SAVE IN GRAPH INDEX
        return self # REQUIRED FROM iadd()!!

    def __isub__(self, i):
        "Remove a schema rule from this SchemaDict"
        g = i[0]
        if g not in self:
            raise KeyError('graph not found in SchemaDict!')
        self[g].remove(i) # REMOVE OLD ENTRY
        if len(self[g]) == 0: # REMOVE EMPTY LIST
            del self[g]
        if len(i) >= 2:
            if isinstance(i[1], types.StringType):
                if i[1] not in self.attrs:
                    raise KeyError('attribute not found in SchemaDict!')
                del self.attrs[i[1]] # REMOVE OLD ENTRY
            else:
                raise TypeError('Attribute name must be a string')
        return self # REQUIRED FROM iadd()!!

    def initInstance(self, obj):
        "Add obj as new node to all graphs referenced by this SchemaDict."
        for g, l in self.items(): # GET ALL OUR RULES
            for s in l:
                if obj not in g:
                    g.__iadd__(obj, (s, ))  # ADD OBJECT TO GRAPH USING RULE s

    def getschema(self, attr=None, graph=None):
        "Return list of schema rules that match attr / graph arguments."
        if attr:
            if attr in self.attrs:
                return [self.attrs[attr]]
        elif graph:
            if graph in self:
                return self[graph]
        else:
            raise ValueError('You must specify an attribute or graph.')
        return [] # DIDN'T FIND ANYTHING


class SchemaList(list):
    "Temporary container for returned schema list, with attached methods"

    def __init__(self, obj):
        self.obj = obj # OBJECT THAT WE'RE DESCRIBING SCHEMA OF
        list.__init__(self) # CALL SUPERCLASS CONSTRUCTOR

    def __iadd__(self, rule):
        "Add a new schema rule to object described by this SchemaList"
        if not hasattr(self.obj, '__schema__'):
            self.obj.__schema__ = SchemaDict()
        self.obj.__schema__ += rule
        return self # REQUIRED FROM iadd()!!

    # PROBABLY NEED AN __isub__() TOO??


######################
# getschema, getnodes, getedges
# these functions are analogous to getattr, except they get graph information

def getschema(o, attr=None, graph=None):
    "Get list of schema rules for object o that match attr / graph arguments."
    found = SchemaList(o)
    attrs = {}
    if hasattr(o, '__schema__'):
        for s in o.__schema__.getschema(attr, graph):
            found.append(s)
            if isinstance(s[1], types.StringType):
                attrs[s[1]] = None
    if attr and len(found) > 0: # DON'T PROCEED
        return found
    if hasattr(o, '__class_schema__'):
        for s in o.__class_schema__.getschema(attr, graph):
            if not isinstance(s[1], types.StringType) or s[1] not in attrs:
                found.append(s) # DON'T OVERWRITE OBJECT __schema__ BINDINGS
    return found


def setschema(o, attr, graph):
    """Bind object to graph, and if attr not None, also bind graph
    to this attribute."""
    if not hasattr(o, '__schema__'):
        o.__schema__ = SchemaDict()
    o.__schema__ += (graph, attr)


def getnodes(o, attr=None, graph=None):
    """Get destination nodes from graph bindings of o, limited to the
    specific attribute or graph if specified"""
    if attr:
        if hasattr(o, '__schema__') and attr in o.__schema__:
            return getattr(o, o.__schema__[attr][2]) # RETURN THE PRODUCT

        if hasattr(o, '__class_schema__') and attr in o.__class_schema__:
            return getattr(o, o.__class_schema__[attr][2]) # RETURN THE PRODUCT
        raise AttributeError('No attribute named %s in object %s' % (attr, o))
    elif graph: # JUST LOOK UP THE GRAPH TRIVIALLY
        return graph[o]
    else: # SHOULD WE GET ALL NODES FROM ALL SCHEMA ENTRIES?  HOW??
        raise ValueError('You must pass an attribute name or graph')


def getedges(o, attr=None, graph=None):
    """Get edges from graph bindings of o, limited to the specific attribute
    or graph if specified"""
    g = getnodes(o, attr, graph) # CAN JUST REUSE THE LOGIC OF getnodes
    if g and hasattr(g, 'edges'):
        return g.edges()
    else:
        return None

########NEW FILE########
__FILENAME__ = seqdb
"""
seqdb contains a set of classes for interacting with sequence databases.

Primary sequence database classes:

  - SequenceDB         - base class for sequence databases
  - SequenceFileDB     - file-based sequence database
  - PrefixUnionDict    - container to combine multiple sequence databases
  - XMLRPCSequenceDB   - XML-RPC-accessible sequence database

Extensions:

  - SeqPrefixUnionDict - extends PrefixUnionDict to automatically add seqs
  - BlastDB            - implements NCBI-style name munging for lookups

Associated sequence classes:

  - FileDBSequence     - sequence associated with a SequenceFileDB
  - XMLRPCSequence     - sequence associated with a XMLRPCSequenceDB

----

SequenceDB provides some basic behaviors for sequence databases:
dictionary behavior, an invert operator interface, and caching for
both sequence objects and sequence intervals.  It also relies on a
'seqInfoDict' attribute to contain summary information about
sequences, so that e.g. slice operations can be done without loading
the entire sequence into memory.  (See below for more info on
seqInfoDict.)

SequenceFileDB extends SequenceDB to contain a file-based database of
sequences.  It constructs a seqLenDict that allows direct on-disk lookup
of sequence intervals.  (See below for more info on seqLenDict.)

PrefixUnionDict provides a unified SequenceDB-like interface to a
collection of sequence databases by combining the database name with
the sequence ID into a new sequence id.  For example, the ID
'genome.chrI' would return the sequence 'chrI' in the 'genome'
database.  This is particularly handy for situations where you want to
have seqdbs of multiple sequence types (DNA, protein, annotations,
etc.) all associated together.

@CTB document XMLRPCSequenceDB.
@CTB document SeqPrefixUnionDict.
@CTB document BlastDB.

----

The seqInfoDict interface
-------------------------

The seqInfoDict attribute of a SequenceDB is a dictionary-like object,
keyed by sequence IDs, with associated values being an information
object containing various attributes.  seqInfoDict is essentially an
optimization that permits other pygr-aware components to access
information *about* sequences without actually loading the entire
sequence.

The only required attribute at the moment is 'length', which is
required by some of the NLMSA code.  However, seqInfoDict is a good
mechanism for the storage of any summary information on a sequence,
and so it may be expanded in the future.

The seqLenDict interface
------------------------

The seqLenDict attribute is specific to a SequenceFileDB, where it
provides a file-backed storage of length and offset sequence metadata.
It is used to implement a key optimization in SequenceFileDB, in which
a sequence's offset within a file is used to read only the required
part of the sequence into memory.  This optimization is particularly
important for large sequences, e.g. chromosomes, where reading the
entire sequence into memory shouldn't be done unless it's necessary.

The seqLenDict is keyed by sequence ID and the associated values are a
2-tuple (length, offset), where the offset indicates the byte offset
within the '.pureseq' index file created for each SequenceFileDB.

get_bound_subclass and the 'self.db' attribute
----------------------------------------------

The SequenceDB constructor calls classutil.get_bound_subclass on its
itemClass.  What does that do, and what is it for?

get_bound_subclass takes an existing class, makes a new subclass of
it, binds the variable 'db' to it, and then calls the _init_subclass
classmethod (if it exists) on the new class.  This has the effect of
creating a new class for each SequenceDB instance, tied specifically
to that instance and initialized by the _init_subclass method.

The main effect of this for SequenceDBs is that for any SequenceDB
descendant, the '.db' attribute is automatically set for each Sequence
retrieved from the database.

CTB: I think this is an optimization?

Caching
-------

@CTB discuss caching.

Pickling sequence databases and sequences
-----------------------------------------

@CTB document pickling issues.
programmer notes:

extending SequenceDB
 - seqInfoDict, itemclass

extending SequenceFileDB
 - seqLenDict
 - using your own itemclass
 - using your own reader

doctests & examples
-------------------

update docs for these classes!

intro:
 - loading a FASTA file
 - using a PUD
   + combining dbs, etc.
   + inverse

Code review issues, short term:

 - @CTB get_bound_subclass stuff refers directly to itemClass to set 'db'.
 - @CTB fix 'import *'s
 - @CTB run lint/checker?
 - @CTB test _create_seqLenDict
 - @CTB XMLRPCSequenceDB vs SequenceFileDB

Some long term issues:

 - it should be possible to remove _SeqLenDictSaver and just combine its
   functionality with _store_seqlen_dict.  --titus 3/21/09

"""

from __future__ import generators
import sys
import os
import UserDict
import weakref

from sequence import *                  # @CTB
from sqlgraph import *                  # @CTB
import classutil
from annotation import AnnotationDB, AnnotationSeq, AnnotationSlice, \
     AnnotationServer, AnnotationClient
import logger
import seqfmt

from dbfile import NoSuchFileError


####
#
# SequenceDB and associated support classes.
#

class _SequenceDBInverse(object):
    """Implements __inverse__ on SequenceDB objects, returning seq name."""

    def __init__(self, db):
        self.db = db

    def __getitem__(self, seq):
        return seq.pathForward.id

    def __contains__(self, seq):
        try:
            return seq.pathForward.db is self.db
        except AttributeError:
            return False


class SequenceDB(object, UserDict.DictMixin):
    """Base class for sequence databases.

    SequenceDB provides a few basic (base) behaviors:
      - dict-like interface to sequence objects each with an ID
      - the ~ (invert) operator returns an 'inverted' database, which is a
        dict-like object that returns sequence names when given a sequence.
      - weakref-based automatic flushing of seq objects no longer in use;
        use autoGC=0 to turn this off.
      - cacheHint() system for caching a given set of sequence
        intervals associated with an owner object, which are flushed
        from cache if the owner object is garbage-collected.

    For subclassing, note that self.seqInfoDict must be set before
    SequenceDB.__init__ is called!

    """
    # class to use for database-linked sequences; no default.
    itemClass = None
    # class to use for sequence slices; see sequence.SeqPath.classySlice.
    itemSliceClass = SeqDBSlice

    # pickling methods & what attributes to pickle.
    __getstate__ = classutil.standard_getstate
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(autoGC=0)

    # define ~ (invert) operator to return a lazily-created _SequenceDBInverse
    __invert__ = classutil.lazy_create_invert(_SequenceDBInverse)

    def __init__(self, autoGC=True, dbname=None, **kwargs):
        """Initialize seq db from filepath or ifile."""
        if autoGC: # automatically garbage collect unused objects
            self._weakValueDict = classutil.RecentValueDictionary(autoGC)
        else:
            self._weakValueDict = {}    # object cache @CTB not tested
        self.autoGC = autoGC

        # override itemClass and itemSliceClass if specified
        self.itemClass = kwargs.get('itemClass', self.itemClass)
        self.itemSliceClass = kwargs.get('itemSliceClass', self.itemSliceClass)

        if self.itemClass is None:
            raise TypeError("must supply itemClass to SequenceDB")

        # get a copy we can modify w/o side effects and bind itemClass.
        kwargs = kwargs.copy()
        kwargs['db'] = self
        classutil.get_bound_subclass(self, 'itemClass', dbname,
                                     subclassArgs=kwargs)

        # guess the sequence type
        self._set_seqtype()

    def __hash__(self):
        """Define a hash function to allow this object to be used as a key."""
        return id(self)

    def _set_seqtype(self):
        """Guess the seqtype from 100 chars of 1st seq if not already known."""
        seqtype = getattr(self, '_seqtype', None)
        if seqtype is not None:
            return

        for seqID in self: # get an iterator
            seq = self[seqID] # get the 1st sequence
            ch100 = str(seq[:100])
            self._seqtype = guess_seqtype(ch100)
            break # only process the 1st sequence!!!

    _cache_max=10000                    # @CTB move? make settable?

    def cacheHint(self, ivalDict, owner):
        """Save a cache hint dict: {id: (start, stop)}.

        @CTB document!
        """
        d={}
        # @CTB refactor, test
        # Build the cache dictionary for owner.
        for id, ival in ivalDict.items():
            if ival[0] < 0: # FORCE IVAL INTO POSITIVE ORIENTATION
                ival=(-ival[1], -ival[0])        # @CTB untested
            if ival[1]-ival[0] > self._cache_max: # TRUNCATE EXCESSIVE LENGTH
                ival=(ival[0], ival[0] + self._cache_max) # @CTB untested
            d[id]=[ival[0], ival[1]]
        try:
            self._cache[owner] = d # ADD TO EXISTING CACHE
        except AttributeError:
            self._cache = weakref.WeakKeyDictionary()  # AUTOMATICALLY REMOVE
            self._cache[owner] = d # FROM CACHE IF owner GOES OUT OF SCOPE

    def strsliceCache(self, seq, start, stop):
        """Get strslice using cache hints, if any available."""
        try:
            cacheDict=self._cache
        except AttributeError:
            raise IndexError('no cache present')
        for owner, d in cacheDict.items():
            try:
                ival = d[seq.id]
            except KeyError:
                continue # NOT IN THIS CACHE, SO SKIP  @CTB untested
            ival_start, ival_stop = ival[:2]
            if start >= ival_start and stop <= ival_stop: # CONTAINED IN ival
                try:
                    s = ival[2] # get seq string from our cache
                except IndexError: # use strslice() to retrieve from storage
                    s = seq.strslice(ival_start, ival_stop, useCache=False)
                    ival.append(s)
                    try: # does owner want to reference this cached seq?
                        save_f = owner.cache_reference
                    except AttributeError:
                        pass # no, so nothing to do
                    else: # let owner control caching in our _weakValueDict
                        save_f(seq)     # # @CTB untested
                return s[start - ival_start:stop - ival_start]
        raise IndexError('interval not found in cache') # @CTB untested

    # these methods should all be implemented on all SequenceDBs.
    def close(self):
        pass # subclass should implement closing of its open resources!

    def __iter__(self):
        return iter(self.seqInfoDict)

    def iteritems(self):
        for seqID in self:
            yield seqID, self[seqID]

    def __len__(self):
        return len(self.seqInfoDict)

    def __getitem__(self, seqID):
        """Retrieve sequence by id, using cache if available."""
        try: # for speed, default case (cache hit) should return immediately
            return self._weakValueDict[seqID]
        except KeyError: # not in cache?  try loading.
            try:
                s = self.itemClass(self, seqID)
            except KeyError:
                raise KeyError("no key '%s' in database %s"
                               % (seqID, repr(self)))
            self._weakValueDict[seqID] = s # save in cache.
            return s

    def keys(self):
        return self.seqInfoDict.keys()

    def __contains__(self, key):
        return key in self.seqInfoDict

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__,
                              self.itemClass.__class__.__name__)

    def clear_cache(self):
        """Empty the cache."""
        self._weakValueDict.clear()

    # these methods should not be implemented for read-only database.
    clear = setdefault = pop = popitem = copy = update = \
            classutil.read_only_error


####
#
# FileDBSequence and SequenceFileDB, and associated support classes.
#

class _FileDBSeqDescriptor(object):
    """Descriptor to retrieve entire sequence from seqLenDict."""

    def __get__(self, obj, objtype):
        length = obj.db.seqLenDict[obj.id][0]
        return obj.strslice(0, length)


class FileDBSequence(SequenceBase):
    """Default sequence object for file-based storage mechanism.

    See SequenceFileDB for the associated database class.

    In general, you should not create objects from this class directly;
    retrieve them from SequenceFileDB objects, instead.

    NOTE: 'self.db' is attached to all instances of this class that come
    from a particular database by 'classutil.get_bound_subclass'.

    """
    seq = _FileDBSeqDescriptor()        # dynamically retrieve 'seq'.
    __reduce__ = classutil.item_reducer # for pickling purposes.

    def __init__(self, db, id):
        self.id = id
        SequenceBase.__init__(self)
        if self.id not in self.db.seqLenDict:
            raise KeyError('sequence %s not in db %s' % (self.id, self.db))

    def __len__(self):
        """Unpack this sequence's length from the seqLenDict."""
        return self.db.seqLenDict[self.id][0]

    def strslice(self, start, end, useCache=True):
        """Access slice of a sequence efficiently, using seqLenDict info."""
        if useCache:                    # If it's in the cache, use that!
            try:
                return self.db.strsliceCache(self, start, end)
            except IndexError:
                pass

        return self.db.strslice(self.id, start, end)


class SequenceFileDB(SequenceDB):
    """Main class for file-based storage of a sequence database.

    By default, SequenceFileDB uses a seqLenDict, a.k.a. a shelve
    index of sequence lengths and offsets, to retrieve sequence slices
    with fseek.  Thus entire chromosomes (for example) do not have to
    be loaded to retrieve a subslice.

    Takes one required argument, 'filepath', which should be the name
    of a FASTA file (or a file whose format is understood by your
    custom reader; see 'reader' kw arg, and the _store_seqlen_dict
    function).

    The SequenceFileDB seqInfoDict interface is a wrapper around the
    seqLenDict created by the __init__ function.

    """
    itemClass = FileDBSequence

    # copy _pickleAttrs and add 'filepath'
    _pickleAttrs = SequenceDB._pickleAttrs.copy()
    _pickleAttrs['filepath'] = 0

    def __init__(self, filepath, reader=None, **kwargs):
        # make filepath a pickleable attribute.
        self.filepath = classutil.SourceFileName(str(filepath))

        fullpath = self.filepath + '.seqlen'
        # build the seqLenDict if it doesn't already exist
        try:
            seqLenDict = classutil.open_shelve(fullpath, 'r')
        except NoSuchFileError:
            seqLenDict = self._create_seqLenDict(fullpath, filepath, reader)

        self.seqLenDict = seqLenDict
        self.seqInfoDict = _SeqLenDictWrapper(self) # standard interface

        # initialize base class.
        dbname = os.path.basename(filepath)
        SequenceDB.__init__(self, filepath=filepath, dbname=dbname, **kwargs)

    def close(self):
        '''close our open shelve index file and _pureseq...'''
        self.seqLenDict.close()
        try:
            do_close = self._pureseq.close
        except AttributeError:
            pass # _pureseq not open yet, so nothing to do
        else:
            do_close()

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.filepath)

    def _create_seqLenDict(self, dictpath, seqpath, reader=None):
        """Create a seqLenDict from 'seqpath' and store in 'dictpath'."""
        seqLenDict = classutil.open_shelve(dictpath, 'n')
        try:
            logger.debug('Building sequence length index...')
            _store_seqlen_dict(seqLenDict, seqpath, reader)
        finally:
            seqLenDict.close() # close after writing, no matter what!
        return classutil.open_shelve(dictpath, 'r') # re-open read-only

    def strslice(self, seqID, start, end, useCache=True):
        """Access slice of a sequence efficiently, using seqLenDict info."""
        # Retrieve sequence from the .pureseq file based on seqLenDict
        # information.
        try:
            ifile=self._pureseq
        except AttributeError:
            fullpath = self.filepath + '.pureseq'
            ifile = file(fullpath, 'rb')
            self._pureseq = ifile

        # Now, read in the actual slice.
        offset = self.seqLenDict[seqID][1]
        ifile.seek(offset + start)
        return ifile.read(end - start)


# Some support classes for the SeqLenDict mechanism.

class BasicSeqInfo(object):
    """Wrapper to provide the correct seqInfoDict-style object information.

    This boils down to providing id, db, length, and possibly offset.

    """

    def __init__(self, seqID, seqDB, length=None):
        self.id = seqID
        self.db = seqDB
        if length is None:
            self.length = len(seqDB[seqID]) # generic but possibly slow
        else:
            self.length = length


class _SeqLenObject(BasicSeqInfo):
    """Wrapper for use with a seqLenDict """

    def __init__(self, seqID, seqDB):
        length, self.offset = seqDB.seqLenDict[seqID]
        BasicSeqInfo.__init__(self, seqID, seqDB, length)


class BasicSeqInfoDict(object, UserDict.DictMixin):
    """Wrapper around SequenceDB.seqLenDict to provide seqInfoDict behavior.
    This basic version just gets the length from the sequence object itself.
    """
    itemClass = BasicSeqInfo

    def __init__(self, db):
        self.seqDB = db

    def __getitem__(self, k):
        return self.itemClass(k, self.seqDB)

    def __len__(self):
        return len(self.seqDB.seqLenDict)

    def __iter__(self):
        return iter(self.seqDB.seqLenDict)

    def keys(self):
        return self.seqDB.seqLenDict.keys()


class _SeqLenDictWrapper(BasicSeqInfoDict):
    """
    The default storage mechanism for sequences implemented by FileDBSequence
    and SequenceFileDB puts everything in seqLenDict, a shelve index of
    lengths and offsets.  This class wraps that dictionary to provide the
    interface that SequenceDB expects to see.

 """
    itemClass = _SeqLenObject


class _SeqLenDictSaver(object):
    """Support for generic reading functions, called by _store_seqlen_dict.

    This allows you to specify your own 'reader' function when
    constructing a FileSequenceDB, e.g. so that you could read
    something other than FASTA files into a seqLenDict.  Pass in this
    function as the 'reader' kwarg to FileSequenceDB.

    Custom reader functions should take a file handle and a filename,
    and return a list of sequence info objects with 'id', 'length',
    and 'sequence' attributes for each sequence in the given
    file/filename.  _SeqLenDictSaver will then construct a '.pureseq'
    file containing the concatenated sequences and fill in the
    seqLenDict appropriately.

    """

    def __init__(self, reader):
        self.reader = reader

    def __call__(self, d, ifile, filename):
        offset = 0L
        pureseq_fp = file(filename + '.pureseq', 'wb')
        try:
            for o in self.reader(ifile, filename):
                # store the length & offset in the seqLenDict
                d[o.id] = o.length, offset
                offset += o.length
                if o.length != len(o.sequence):
                    raise ValueError('length does not match sequence: %s,%d'
                                     % (o.id, o.length))
                pureseq_fp.write(o.sequence)
        finally:
            pureseq_fp.close()


def _store_seqlen_dict(d, filename, reader=None, mode='rU'):
    """Store sequence lengths in a dictionary, e.g. a seqLenDict.

    Used by SequenceFileDB._create_seqLenDict.

    The 'reader' function implements a custom sequence format reader;
    by default, _store_seqlen_dict uses seqfmt.read_fasta_lengths,
    which reads FASTA-format files.  See _SeqLenDictSaver for
    information on building a custom 'reader', and see the seqdb docs
    for an example.

    """
    # if a custom reader function was passed in, run that.
    builder = seqfmt.read_fasta_lengths
    if reader is not None:
        builder = _SeqLenDictSaver(reader)

    ifile = file(filename, mode)
    try:
        builder(d, ifile, filename) # run the builder on our sequence set
    finally:
        ifile.close()


####
#
# class PrefixUnionDict and associated support classes.
#

class _PrefixUnionDictInverse(object):
    """Provide inverse (~) operator behavior for PrefixUnionDicts.

    This enables ~pud to return a database that, given a sequence
    object, returns the corresponding key (prefix.id) to retrieve that
    sequence object in the pud.

    """

    def __init__(self, db):
        self.db = db

    def __getitem__(self, ival):
        seq = ival.pathForward # get the top-level sequence object
        try: # for speed, normal case should execute immediately
            prefix = self.db.dicts[seq.db]
        except KeyError:
            try:
                # @CTB abstraction boundary violation! keep? how test?
                if seq.pathForward._anno_seq.db in self.db.dicts:
                    raise KeyError('''\
this annotation is not in the PrefixUnion, but its sequence is.
You can get that using its \'sequence\' attribute.''')
            except AttributeError:
                pass
            raise KeyError('seq.db not in PrefixUnionDict')

        return prefix + self.db.separator + str(seq.id)

    def __contains__(self, seq):
        try:
            return seq.pathForward.db in self.db.dicts
        except AttributeError:
            return False


class _PrefixUnionMemberDict(object, UserDict.DictMixin):
    """
    @CTB confusing/inappropriate use of a dict interface! keep??
    @CTB document.
    'd[prefix]=value; d[k] returns value if k is a member of prefix'
    """

    def __init__(self, puDict, default=None,
                 attrMethod=lambda x: x.pathForward.db):
        self.values = {}
        self.puDict = puDict
        self._attrMethod = attrMethod
        if default is not None:
            self.default = default      # @CTB can we use setdefault for this?

    def keys(self):
        return self.puDict.prefixDict.keys()

    possibleKeys = keys                 # legacy interface (?)

    def __setitem__(self, k, v):
        if k not in self.puDict.prefixDict:
            raise KeyError('key %s is not a valid union prefix string!' % k)
        new_k = self.puDict.prefixDict[k]
        self.values[new_k] = v

    def __getitem__(self, k):
        try:
            db = self._attrMethod(k)
        except AttributeError:
            raise TypeError('wrong key type? _attrMethod() failed.')

        if db not in self.values:
            try:
                return self.default
            except AttributeError:      # no default value - raise KeyError.
                raise KeyError('key not a member of this union!')

        return self.values[db]


class PrefixUnionDict(object, UserDict.DictMixin):
    """Interface to a set of sequence DBs, each assigned a unique prefix.

    For example, the sequence ID 'foo.bar' would unpack to ID 'bar' in
    the dictionary associated with the prefix 'foo'.  This is a useful
    way to combine disparate seqdbs into a single db, without actually
    altering the individual seqdbs.

    PrefixUnionDicts can be created in one of two ways: either
      - pass in a dictionary containing prefix-to-seqdb mappings as
        'prefixDict', or
      - pass in a header file containing the information necessary to create
        such a dictionary.

    In the latter case, see the 'writeHeaderFile' method for format
    information.  The optional kwarg 'trypath' contains a list of
    directories to search for the database file named in each line.
    The optional kwarg 'dbClass' specifies the database class to use
    to load each sequence file; it defaults to SequenceFileDB.

    The default ID separator is '.'; use the 'separator' kwarg to
    change it.

    @CTB trypath => trypaths?

    """
    # define ~ (invert) operator to return a lazily-created _PUDInverse.
    __invert__ = classutil.lazy_create_invert(_PrefixUnionDictInverse)

    def __init__(self, prefixDict=None, separator='.', filename=None,
                 dbClass=SequenceFileDB, trypath=None):
        # read union header file
        if filename is not None:
            if prefixDict:
                raise TypeError('''
cannot create with prefixDict and filename both!''')

            if trypath is None:
                trypath = [os.path.dirname(filename)]
            ifile = file(filename, 'rU')
            try:
                it = iter(ifile)
                # Remove leading/trailing CR+LF.
                separator = it.next().strip('\r\n')
                prefixDict = {}
                for line in it:
                    prefix, filepath=line.strip().split('\t')[:2]
                    try:
                        dbfile = classutil.search_dirs_for_file(filepath,
                                                                trypath)
                        db = dbClass(dbfile)
                    except IOError:
                        for db in prefixDict.values():
                            db.close() # close databases before exiting
                        raise IOError('''\
    unable to open database %s: check path or privileges.
    Set 'trypath' to give a list of directories to search.''' % filepath)
                    else:
                        prefixDict[prefix] = db
            finally:
                ifile.close()

        self.separator = separator
        if prefixDict is not None:
            self.prefixDict = prefixDict
        else:
            self.prefixDict = {}

        # also create a reverse mapping
        d = {}
        for k, v in self.prefixDict.items():
            d[v] = k

        self.dicts = d
        self.seqInfoDict = _PUDSeqInfoDict(self) # supply standard interface

    def format_id(self, prefix, seqID):
        return prefix + self.separator + seqID

    def get_prefix_id(self, k):
        """Subdivide a key into a prefix and ID using the given separator."""
        try:
            t = k.split(self.separator, 2) # split into no more than 3 fields
        except AttributeError:
            raise KeyError('key should be a string! ' + repr(k))
        l = len(t)
        if l == 2:
            return t
        elif l<2:
            raise KeyError('invalid id format; no prefix: ' + k)
        else: # id contains separator character?
            prefix = t[0] # assume prefix doesn't contain separator @CTB untested
            seqID = k[len(prefix) + 1:] # skip past prefix
            return prefix, seqID

    def get_subitem(self, d, seqID):
        # try int key first
        try:
            return d[int(seqID)]
        except (ValueError, KeyError, TypeError):
            pass

        # otherwise, use default (str) key
        try:
            return d[seqID]
        except KeyError:
            raise KeyError("no key '%s' in %s" % (seqID, repr(d)))

    def __getitem__(self, k):
        """For 'foo.bar', return 'bar' in dict associated with prefix 'foo'"""
        prefix, seqID = self.get_prefix_id(k)
        try:
            d = self.prefixDict[prefix]
        except KeyError, e:
            raise KeyError("no key '%s' in %s" % (k, repr(self)))
        return self.get_subitem(d, seqID)

    def __contains__(self, k):
        """Is the given ID in our PrefixUnionDict?"""
        # try it out as an ID.
        if isinstance(k, str):
            try:
                (prefix, id) = self.get_prefix_id(k)
                return id in self.prefixDict[prefix]
            except KeyError:
                return False

        # otherwise, try treating key as a sequence.
        # @CTB inconsistent with 'getitem'.
        try:
            db = k.pathForward.db
        except AttributeError:
            raise AttributeError('key must be a sequence with db attribute!')
        return db in self.dicts

    def has_key(self, k):
        return self.__contains__(k)

    def __iter__(self):
        for p, d in self.prefixDict.items():
            for id in d:
                yield self.format_id(p, id)

    def keys(self):
        return list(self.iterkeys())

    def iterkeys(self):
        return iter(self)

    def iteritems(self):
        for p, d in self.prefixDict.items():
            for id, seq in d.iteritems():
                yield self.format_id(p, id), seq

    def getName(self, ival):
        """For a given sequence, return a fully qualified name, 'prefix.id'."""
        seq = ival.pathForward # get the top-level sequence object
        return self.dicts[seq.db] + self.separator + seq.id

    def newMemberDict(self, **kwargs):  # @CTB not used; necessary?
        """return a new member dictionary (empty)"""
        return _PrefixUnionMemberDict(self, **kwargs)

    def writeHeaderFile(self, filename):  # @CTB not used; necessary?
        """Save a header file, suitable for later re-creation."""
        ifile = file(filename, 'w')
        print >>ifile, self.separator
        for k, v in self.prefixDict.items():
            try:
                print >>ifile, '%s\t%s' % (k, v.filepath)
            except AttributeError:
                raise AttributeError('''\
seq db '%s' has no filepath; you may be able to save this to worldbase,
but not to a text HeaderFile!''' % k)
        ifile.close()

    def __len__(self):
        n=0
        for db in self.dicts:
            n += len(db)
        return n

    def cacheHint(self, ivalDict, owner=None):  # @CTB untested
        '''save a cache hint dict of {id:(start,stop)}'''
        d={}
        # extract separate cache hint dict for each prefix
        for longID, ival in ivalDict.items():
            prefix, seqID = self.get_prefix_id(longID)
            d.setdefault(prefix, {})[seqID] = ival
        for prefix, seqDict in d.items():
            try:
                m = self.prefixDict[prefix].cacheHint
            except AttributeError: # subdict can't cacheHint(), so just ignore
                pass
            else:
                # pass cache hint down to subdictionary
                m(seqDict, owner)

    # not clear what this should do for PrefixUnionDict
    copy = setdefault = update = classutil.method_not_implemented

    # these methods should not be implemented for read-only database.
    clear = pop = popitem = classutil.read_only_error


class _PrefixDictInverseAdder(_PrefixUnionDictInverse):
    """Inverse class for SeqPrefixUnionDict; adds sequences when looked up.

    @CTB is getName only used by __getitem__?  Make private?
    """

    def getName(self, seq):
        """Find in or add the given sequence to the inverse of a PUD."""
        try:
            return _PrefixUnionDictInverse.__getitem__(self, seq)
        except AttributeError: # no seq.db?  treat as a user sequence.
            new_id = 'user' + self.db.separator + seq.pathForward.id
            # check to make sure it's already in the user seq db...
            _ = self.db[new_id]
            return new_id

    def __getitem__(self, seq):
        """__getitem__ interface that calls getName."""
        try:
            return self.getName(seq)
        except KeyError:
            if not self.db.addAll:
                raise

            # if we should add, add seq & re-try.
            self.db += seq
            return self.getName(seq)


class SeqPrefixUnionDict(PrefixUnionDict):
    """SeqPrefixUnionDict provides += functionality to add seqs to a PUD.

    See the __iadd__ method for details.

    If addAll is True, then looking a sequence up in the inverse db will
    automatically add it to the PrefixUnionDict.
    """

    __invert__ = classutil.lazy_create_invert(_PrefixDictInverseAdder)

    def __init__(self, addAll=False, **kwargs):
        PrefixUnionDict.__init__(self, **kwargs)

        # override default PrefixUnionDict __invert__ to add sequences;
        # see classutil.lazy_create_invert.
        self.addAll = addAll  # see _PrefixDictInverseAdder behavior.

    def __iadd__(self, k):
        """Add a sequence or database to the PUD, with a unique prefix.

        NOTE: __iadd__ must return self.

        """
        # seq or db already present?
        if k in (~self):
            return self

        db = getattr(k, 'db', None)
        if db is None:                  # annotation sequence?
            db = getattr(k.pathForward, 'db', None) # @CTB untested

        if db is None:  # this is a user sequence, with no container; create.
            if 'user' not in self.prefixDict:
                d = KeepUniqueDict()
                self._add_prefix_dict('user', d)
            else:
                d = self.prefixDict['user']

            # now add the sequence
            d[k.pathForward.id] = k.pathForward
            return self

        # already contain?  nothing to do.
        if db in self.dicts:            # @CTB can this 'if' ever be true?
            return self

        # ok, not present; add, with a unique name.  does it have
        # _persistent_id?
        try:
            name = db._persistent_id.split('.')[-1]
        except AttributeError:          # no; retrieve from filepath?
            name = getattr(db, 'filepath', None)
            if name:                    # got one; clean up.
                name = os.path.basename(name)
                name = name.split('.')[0]
            else:                       # generate one.
                name = 'noname%d' % len(self.dicts)

            if name in self.prefixDict:
                logger.debug('''
It appears that two different sequence databases are being assigned
the same prefix ("%s").  For this reason, the attempted automatic
construction of a PrefixUnionDict for you cannot be completed!  You
should instead construct a PrefixUnionDict that assigns a unique
prefix to each sequence database, and supply it directly as the
seqDict argument to the NLMSA constructor.''' % id)
                raise ValueError('''\
cannot automatically construct PrefixUnionDict''')

        self._add_prefix_dict(name, db)

        return self

    def _add_prefix_dict(self, name, d):
        self.prefixDict[name] = d
        self.dicts[d] = name


class _PUDSeqInfoDict(object, UserDict.DictMixin):
    """A wrapper object supplying a standard seqInfoDict interface for PUDs.

    This class simply provides a standard dict interface that rewrites
    individual sequence IDs into the compound PrefixUnionDict seq IDs
    on the fly.

    """

    def __init__(self, db):
        self.seqDB = db

    def __iter__(self):
        return iter(self.seqDB)

    def keys(self):
        return list(self.iterkeys())

    def iterkeys(self):
        for (k, v) in self.iteritems():
            yield k

    def itervalues(self):
        for (k, v) in self.iteritems():
            yield v

    def iteritems(self):
        for p, d in self.seqDB.prefixDict.items():
            for seqID, info in d.seqInfoDict.iteritems():
                yield self.seqDB.format_id(p, seqID), info

    def __getitem__(self, k):
        prefix, seqID = self.seqDB.get_prefix_id(k)
        db = self.seqDB.prefixDict[prefix]
        return self.seqDB.get_subitem(db.seqInfoDict, seqID)

    def has_key(self, k):
        return k in self.seqDB

#
# @CTB stopped review here. ###################################################
#

class BlastDB(SequenceFileDB):          # @CTB untested?
    '''Deprecated interface provided for backwards compatibility.
    Provides blast() and megablast() methods for searching your seq db.
    Instead of this, you should use the blast.BlastMapping, which provides
    a graph interface to BLAST, or MegablastMapping for megablast.'''

    def __reduce__(self): # provided only for compatibility w/ 0.7 clients
        return (classutil.ClassicUnpickler, (self.__class__,
                                             self.__getstate__()))

    def __init__(self, filepath=None, blastReady=False, blastIndexPath=None,
                 blastIndexDirs=None, **kwargs):
        """format database and build indexes if needed. Provide filepath
        or file object"""
        SequenceFileDB.__init__(self, filepath, **kwargs)

    def __repr__(self):
        return "<BlastDB '%s'>" % (self.filepath)

    def blast(self, seq, al=None, blastpath='blastall',
              blastprog=None, expmax=0.001, maxseq=None, verbose=True,
              opts='', **kwargs):
        'run blast with the specified parameters, return NLMSA alignment'
        blastmap = self.formatdb()
        return blastmap(seq, al, blastpath, blastprog, expmax, maxseq,
                        verbose, opts, **kwargs)

    def megablast(self, seq, al=None, blastpath='megablast', expmax=1e-20,
                  maxseq=None, minIdentity=None, maskOpts='-U T -F m',
                  rmPath='RepeatMasker', rmOpts='-xsmall',
                  verbose=True, opts='', **kwargs):
        'run megablast with the specified parameters, return NLMSA alignment'
        from blast import MegablastMapping
        blastmap = self.formatdb(attr='megablastMap',
                                 mapClass=MegablastMapping)
        return blastmap(seq, al, blastpath, expmax, maxseq, minIdentity,
                        maskOpts, rmPath, rmOpts, verbose, opts, **kwargs)

    def formatdb(self, filepath=None, attr='blastMap', mapClass=None):
        'create a blast mapping object if needed, and ensure it is indexed'
        try: # see if mapping object already exists
            blastmap = getattr(self, attr)
        except AttributeError:
            if mapClass is None: # default: BlastMapping
                from blast import BlastMapping
                mapClass = BlastMapping
            blastmap = mapClass(self)
            setattr(self, attr, blastmap) # re-use this in the future
        blastmap.formatdb(filepath) # create index file if not already present
        return blastmap


class BlastDBXMLRPC(BlastDB):
    'XMLRPC server wrapper around a standard BlastDB'
    xmlrpc_methods = dict(getSeqLen=0, get_strslice=0, getSeqLenDict=0,
                          get_db_size=0, get_seqtype=0,
                          strslice='get_strslice')

    def getSeqLen(self, id):
        'get sequence length, or -1 if not found'
        try:
            return len(self[id])
        except KeyError:
            return -1  # SEQUENCE OBJECT DOES NOT EXIST

    def getSeqLenDict(self):
        'return seqLenDict over XMLRPC'
        d = {}
        for k, v in self.seqLenDict.items():
            d[k] = v[0], str(v[1]) # CONVERT TO STR TO ALLOW OFFSET>2GB
        return d # XML-RPC CANNOT HANDLE INT > 2 GB, SO FORCED TO CONVERT...

    def get_db_size(self):
        return len(self)

    def get_strslice(self, id, start, stop):
        '''return string sequence for specified interval
        in the specified sequence'''
        if start < 0: # HANDLE NEGATIVE ORIENTATION
            return str((-(self[id]))[-stop:-start])
        else: # POSITIVE ORIENTATION
            return str(self[id][start:stop])

    def get_seqtype(self):
        return self._seqtype


class XMLRPCSequence(SequenceBase):
    "Represents a sequence in a blast database, accessed via XMLRPC"

    def __init__(self, db, id):
        self.length = db.server.getSeqLen(id)
        if self.length <= 0:
            raise KeyError('%s not in this database' % id)
        self.id = id
        SequenceBase.__init__(self)

    def strslice(self, start, end, useCache=True):
        "XMLRPC access to slice of a sequence"
        if useCache:
            try:
                return self.db.strsliceCache(self, start, end)
            except IndexError: # NOT FOUND IN CACHE
                pass # JUST USE OUR REGULAR XMLRPC METHOD
        # Get from XMLRPC.
        return self.db.server.get_strslice(self.id, start, end)

    def __len__(self):
        return self.length


class XMLRPCSeqLenDescr(object):
    'descriptor that returns dictionary of remote server seqLenDict'

    def __init__(self, attr):
        self.attr = attr

    def __get__(self, obj, objtype):
        '''only called if attribute does not already exist. Saves result
        as attribute'''
        d = obj.server.getSeqLenDict()
        for k, v in d.items():
            d[k] = v[0], int(v[1]) # CONVERT OFFSET STR BACK TO INT
        obj.__dict__[self.attr] = d # PROVIDE DIRECTLY TO THE __dict__
        return d


class XMLRPCSequenceDB(SequenceDB):
    'XMLRPC client: access sequence database over XMLRPC'
    itemClass = XMLRPCSequence # sequence storage interface
    seqLenDict = XMLRPCSeqLenDescr('seqLenDict') # INTERFACE TO SEQLENDICT

    def __init__(self, url, name, *args, **kwargs):
        import coordinator
        self.server = coordinator.get_connection(url, name)
        self.url = url
        self.name = name
        self.seqInfoDict = _SeqLenDictWrapper(self)
        SequenceDB.__init__(self, *args, **kwargs)

    def __reduce__(self): # provided only for compatibility w/ 0.7 clients
        return (classutil.ClassicUnpickler, (self.__class__,
                                             self.__getstate__()))

    def __getstate__(self): # DO NOT pickle self.itemClass! We provide our own.
        return dict(url=self.url, name=self.name) # just need XMLRPC info

    def __len__(self):
        return self.server.get_db_size()

    def __contains__(self, k):
        if self.server.getSeqLen(k)>0:
            return True
        else:
            return False

    def _set_seqtype(self):
        'efficient way to determine sequence type of this database'
        try: # if already known, no need to do anything
            return self._seqtype
        except AttributeError:
            self._seqtype = self.server.get_seqtype()
            return self._seqtype

########NEW FILE########
__FILENAME__ = sequence

from __future__ import generators
import types
from sequtil import *


NOT_ON_SAME_PATH = -2


class ReadOnlyAttribute(object):

    def __init__(self, attr):
        self.attr = attr

    def __get__(self, obj, klass):
        return getattr(obj, self.attr)


###################################################################
#
# INTERVAL - INTERVAL MAPPING
# CORRECTLY HANDLES SCALING AND ORIENTATION TRANSFORMATIONS
# ASSUMES A SIMPLE SCALAR TRANSFORMATION FROM ONE COORD SYSTEM
# TO THE OTHER.  DOES NOT HANDLE INDELS WITHIN THE MAPPING!

class IntervalTransform(object):
    "Represents coordinate transformation from one interval to another"
    srcPath=ReadOnlyAttribute('_srcPath') # PREVENT USER FROM MODIFYING THESE!
    destPath=ReadOnlyAttribute('_destPath')

    def __init__(self, srcPath, destPath, edgeInfo=None,
                 edgeAttr=None, edgeIndex=None):
        "MAP FROM srcPath -> destPath"
        self.scale = len(destPath) / float(len(srcPath))
        self._srcPath = srcPath
        self._destPath = destPath
        if edgeInfo != None and edgeAttr != None:
            try: # GET EDGE INFO IF PRESENT
                edgeInfo = getattr(edgeInfo, edgeAttr)
            except AttributeError:
                edgeInfo = None
        if edgeInfo != None:
            if edgeIndex != None:
                edgeInfo = edgeInfo[edgeIndex]
            self.edgeInfo = edgeInfo

    def xform(self, i):
        'transform int srcPath local coord to destPath local coord'
        return int(i * self.scale)

    def xformBack(self, i):
        'transform int destPath local coord to srcPath local coord'
        return int(i / self.scale)

    def getStartStop(self, srcPath, ourPath):
        'compute srcPath start,stop in ourPath local coords'
        if srcPath.path is ourPath.path:
            return srcPath.start - ourPath.start, srcPath.stop - ourPath.start
        try:
            if srcPath.path._reverse is ourPath.path:
                return -(srcPath.start) - ourPath.start,\
                       -(srcPath.stop) - ourPath.start
        except AttributeError:
            pass
        raise ValueError('sequence mismatch: argument not from this seq')

    def __call__(self, srcPath):
        """Apply this transformation to an interval
           NB: it is not restricted to the domain of this transform,
           and thus can extend BEYOND the boundaries of this transform.
           If you want it clipped use [] interface instead of ()."""
        start, stop = self.getStartStop(srcPath, self.srcPath)
        return SeqPath(self.destPath, self.xform(start), self.xform(stop),
                       relativeToStart=True)

    def reverse(self, destPath):
        "reverse transform an interval"
        start, stop = self.getStartStop(destPath, self.destPath)
        return SeqPath(self.srcPath, self.xformBack(start),
                       self.xformBack(stop), relativeToStart=True)

    def __getitem__(self, srcPath): # PROVIDE DICT-LIKE INTERFACE
        """intersect srcPath with domain of this transform, then return
        transform to target domain coordinates"""
        return self(srcPath * self.srcPath)

    def __iter__(self):
        yield self.srcPath

    def items(self):
        yield self.srcPath, self.destPath

    def __getattr__(self, attr):
        "provide transparent wrapper for edgeInfo attributes"
        try:
            return getattr(self.__dict__['edgeInfo'], attr)
        except (KeyError, AttributeError): # RAISE EXCEPTION IF NOT FOUND!
            raise AttributeError('neither IntervalTransform nor edgeinfo \
                                 has attr ' + attr)

    def repr_dict(self):
        "Return compact dictionary representing this interval mapping"
        s = self.srcPath.repr_dict() # GET REPR OF BOTH INTERVALS
        d = self.destPath.repr_dict()
        out= {}
        for k, val in s.items(): # ADD PREFIX TO EACH ATTR
            out['src_' + k] = val
            out['dest_' + k] = d[k]
        try:
            e = self.edgeInfo.repr_dict() # GET EDGE INFO IF PRESENT
        except AttributeError:
            pass
        else:
            out.update(e) # SAVE EDGE INFO DATA
        return out

    def nidentity(self):
        "calculate total #identity matches between srcPath and destPath"
        nid = 0
        src = str(self.srcPath).upper()
        dest = str(self.destPath).upper()
        slen = len(src)
        i = 0
        while i < slen:
            if src[i] == dest[i]:
                nid += 1
            i += 1
        return nid

    def percent_id(self):
        "calculate fractional identity for this pairwise alignment"
        return self.nidentity / float(len(self.srcPath))


###################################################################
#
# SINGLE LETTER GRAPH INTERFACE CLASSES
# INSTANTIATED ON THE FLY TO PROVIDE LETTER GRAPH INTERFACE

class LetterEdgeDescriptor(object):
    "cached dict of sequences traversing this edge"

    def __get__(self, edge, objtype):
        try:
            return edge._seqs
        except AttributeError:
            edge._seqs = edge.origin.getEdgeSeqs(edge.target)
            return edge._seqs


class LetterEdge(object):
    "represents an edge from origin -> target. seqs returns its sequences"
    seqs = LetterEdgeDescriptor()

    def __init__(self, origin, target):
        self.origin = origin
        self.target = target

    def __iter__(self):
        'generate origin seqpos for sequences that traverse this edge'
        for seq in self.seqs:
            # Reduce 1:many schema to 1:1, discard edge information.
            yield self.origin.getSeqPos(seq)

    def iteritems(self):
        'generate origin,target seqpos for sequences that traverse this edge'
        for seq in self.seqs: # REDUCE 1:MANY SCHEMA TO 1:1, DISCARD EDGE INFO
            yield self.origin.getSeqPos(seq), self.target.getSeqPos(seq)

    def __getitem__(self, k):
        '''return origin,target seqpos for sequence k; raise KeyError if
        not in this edge'''
        try:
            k = k.path
        except AttributeError:
            raise TypeError('k not a valid sequence: it has no path attribute')
        return (self.origin.getSeqPos(k.path), self.target.getSeqPos(k.path))

    def __cmp__(self, other):
        'two edge objects match if they link identical nodes'
        try:
            if self.origin == other.origin and self.target == other.target:
                return 0 # REPORT A MATCH
        except AttributeError: # other MUST BE A DIFFERENT TYPE, SO NO MATCH
            pass
        return cmp(id(self), id(other))


def absoluteSlice(seq, start, stop):
    '''get slice of top-level sequence object, in absolute coordinates.
    This method calls getitem on the top-level sequence object
    i.e. seq.pathForward'''
    try:
        if start < 0: # REVERSE ORIENTATION
            return -(seq.pathForward[-stop:-start])
        else: # FORWARD ORIENTATION
            return seq.pathForward[start:stop]
    except AttributeError:
        if seq is None:
            return slice(start, stop)


def relativeSlice(seq, start, stop):
    '''get slice of this sequence object, in relative coordinates.
    This method calls getitem on the top-level sequence object
    i.e. seq.pathForward'''
    if start < 0: # REVERSE ORIENTATION
        return -(seq[-stop: -start])
    else: # FORWARD ORIENTATION
        return seq[start: stop]


def sumSliceIndex(i, myslice, relativeToStart):
    '''Adjust index value either relative to myslice.start (positive indexes)
    or relative to myslice.stop (negative indexes).  Handle the case where
    i is None or myslice is None appropriately.
    '''
    if myslice is None: # NO OBJECT, SO NOTHING TO DO...
        return i
    if i is None:
        i = 0
    i *= myslice.step
    if relativeToStart:
        return i + myslice.start
    else:
        return i + myslice.stop


class SeqOriDescriptor(object):
    "Get orientation of sequence interval"

    def __get__(self, seq, objtype):
        if seq.start >= 0:
            return 1 # FORWARD ORIENTATION
        else:
            return -1 # REVERSE ORIENTATION


class PathForwardDescr(object):
    'get the top-level forward sequence object'

    def __get__(self, seq, objtype):
        if seq.orientation > 0:
            return seq.path
        else:
            return seq.path._reverse


class AbsIntervalDescr(object):
    'get the top-level forward sequence object'

    def __get__(self, seq, objtype):
        if seq.orientation > 0:
            return seq.start, seq.stop
        else:
            return -(seq.stop), -(seq.start)


class SeqPath(object):
    '''Base class for specifying a path, ie. sequence interval.
    This implementation takes a sequence object as initializer
    and simply represents the interval as a slice of the sequence.'''
    orientation=SeqOriDescriptor()  # COMPUTE ORIENTATION AUTOMATICALLY
    pathForward=PathForwardDescr()  # GET THE TOP-LEVEL FORWARD SEQUENCE OBJ
    _abs_interval=AbsIntervalDescr()

    def __init__(self, path, start=0, stop=None, step=None, reversePath=False,
                 relativeToStart=False, absoluteCoords=False):
        '''Return slice of path[start:stop:step].
        NB: start>stop means reverse orientation, i.e. (-path)[-stop:-start]
        start/stop are LOCAL coordinates relative to the specified path
        By default, start/stop are interpreted in the usual Python slicing way,
        i.e. a negative start value is interpreted as len(path)-start.
        The relativeToStart option turns off this behavior, so that negative
        values are interpreted as negative coordinates in the local coordinate
        system of path.

        absoluteCoords option allows intervals to be created using
        Pygr's internal coordinate convention i.e.
        -20,-10 --> -(path.pathForward[10:20])
        '''
        if reversePath: # create top-level negative orientation path
            start = -(path.stop)
            stop = 0
            self._reverse = path
            path = None # make this a top-level path object
        if absoluteCoords: # THIS OPTION PROVIDES TRANSPARENT WAY TO CREATE
            if start >= 0:   # INTERVALS USING start,stop PAIRS THAT FOLLOW
                path = path.pathForward # OUR INTERNAL SIGN CONVENTION
            else: # i.e. start<0 MEANS REVERSE ORIENTATION!
                path = - (path.pathForward)
        else: # ADJUST start,stop ACCORDING TO path.start / path.stop
            start = sumSliceIndex(start, path, relativeToStart or start is None
                                  or start>=0)
            stop = sumSliceIndex(stop, path, relativeToStart or
                                 (stop is not None and stop>=0))
        if start is not None and stop is not None and start>stop:
            start = -start # start>stop MEANS REVERSE ORIENTATION!
            stop = -stop
            if path is not None:
                path = -path
        if path is not None: # perform bounds checking
            if start < path.path.start:
                start = path.path.start
            if stop > path.path.stop:
                stop = path.path.stop
        if start is None or stop is None or start>=stop:
            raise IndexError('cannot create empty sequence interval!')
        self.start = start
        self.stop = stop
        if step is None:
            step = 1
        if path is None:
            self.path = self
            self.step = step
        else: # STORE TOP-LEVEL SEQUENCE PATH...
            self.path = path.path
            self.step = step * path.step

    def classySlice(self, path, *l, **kwargs):
        'create a subslice using appropriate class based on container'
        try: # if db provides a class to use for slices, use it.
            klass = path.pathForward.db.itemSliceClass
        except AttributeError:
            klass = SeqPath # default: just use generic slice class
        return klass(path, *l, **kwargs) # construct the slice

    def absolute_slice(self, start, stop):
        'get slice of top-level sequence, using absolute coords'
        return self.classySlice(self, start, stop, absoluteCoords=True)

    def __getitem__(self, k):
        if isinstance(k, types.IntType):
            if k == -1: # HAVE TO HANDLE THIS CASE SPECIALLY
                k = slice(k, None, 1) # -1 IS LAST LETTER, SO [-1:None] slice
            else: # REGULAR CASE, JUST [k:k+1] slice
                k = slice(k, k + 1, 1)
        if isinstance(k, types.SliceType): # GET AN INTERVAL USING slice
            return self.classySlice(self, k.start, k.stop, k.step)
        elif isinstance(k, SeqPath): # MODEL SEQ AS GRAPH
            if k.path is not self.path:
                raise KeyError('node is not in this sequence!')
            try:
                target = self.classySlice(self.path, k.stop,
                                          k.stop + len(k) * k.step, k.step)
                return {target: LetterEdge(k, target)}
            except IndexError: # OUT OF BOUNDS, SO NO NEXT NODE
                return {}
        raise KeyError('requires a slice object or integer key')

    def __len__(self):
        if self.path is self and self.orientation < 0:
            return len(self._reverse) # GET LENGTH FROM FORWARD SEQUENCE
        # Get the number of results from iter(self).
        d = (self.stop - self.start) / self.step
        if d > 0: # IF stop - start < step, d WILL BE ZERO -- PREVENT THAT!
            return d
        else:
            # Never return 0 length... Bounds checking ensures non-empty ival.
            return 1

    ################################ LETTER GRAPH METHODS: JUST A LINEAR GRAPH
    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def iteritems(self):
        'letter graph iterator over (node1, {node2: edge}) tuples'
        src = self[0] # GET 1ST LETTER
        for i in range(1, len(self)): # ITERATE OVER ALL ADJACENT PAIRS
            target = self[i]
            yield src, {target: LetterEdge(src, target)}
            src = target
        yield src, {} # LAST LETTER HAS NO EDGES

    def getEdgeSeqs(self, other):
        'return dict of sequences that traverse edge from self -> other'
        if self.path is other.path and self.stop == other.start:
            return {self.path: self.stop - self.step}
        else:
            return {}

    def getSeqPos(self, seq):
        'get seq interval corresponding to this node in sequence graph'
        if seq.path is self.path:
            return self
        raise KeyError('seq not on this path!')

    ################################ INTERVAL COMPOSITION OPERATORS
    def __hash__(self):
        'ensure that same seq intervals match in dict'
        return id(self.path)^hash(self.start)^hash(self.stop)

    def __cmp__(self, other):
        'ensure that same seq intervals match in cmp()'
        if not isinstance(other, SeqPath):
            return -1
        if self.path is other.path:
            return cmp((self.start, self.stop), (other.start, other.stop))
        else:
            return NOT_ON_SAME_PATH
            #raise TypeError('SeqPath not comparable, not on same path: %s, %s'
            #                % (self.path, other.path))

    def __contains__(self, k):
        # PUT OTHER LOGIC HERE FOR CHECKING WHETHER INTERVAL IS CONTAINED...
        if isinstance(k, SeqPath):
            if k.path == self.path and self.start <= k.start and \
               k.stop <= self.stop:
                return True
            else:
                return False
        elif isinstance(k, types.IntType):
            return self.start <= k and k < self.stop

    def overlaps(self, p):
        "check whether two paths on same seq overlap"
        if self.path is not p.path:
            return False
        if (self.start <= p.start and p.start < self.stop) or \
               (p.start <= self.start and self.start < p.stop):
            return True
        else:
            return False

    def __mul__(self, other):
        "find intersection of two intervals"
        if isinstance(other, SeqPath):
            if self.path is not other.path:
                return None
            start=max(self.start, other.start)
            stop=min(self.stop, other.stop)
            if start < stop:
                if stop == 0:
                    # Have to handle the boundary case specially because of
                    # Python conventions.
                    stop = None
                return self.classySlice(self.path, start, stop)
            else:
                return None
        else:
            raise TypeError('SeqPath can only intersect SeqPath')

    def __div__(self, other):
        "return transform from other -> self coordinate systems"
        return IntervalTransform(other, self)

    def __neg__(self):
        "return same interval in reverse orientation"
        try:
            if self.seqtype() == PROTEIN_SEQTYPE:
                raise ValueError('protein sequence has no reverse \
                                 orientation!')
        except AttributeError:
            pass # ALLOW UNTYPED SEQ OBJECTS TO BE REV-COMPD
        if self is self.path: # TOP-LEVEL SEQUENCE OBJECT
            try:
                return self._reverse # USE EXISTING RC OBJECT FOR THIS SEQ
            except AttributeError: #  CREATE ONLY ONE RC FOR THIS SEQUENCE
                self._reverse = self.classySlice(self, reversePath=True)
                return self._reverse
        elif self.orientation > 0: # FORWARD ORI: JUST REVERSE INDICES
            return self.classySlice(self.path, self.stop, self.start,
                                    self.step) #SWAP ==> RC
        else: # REVERSE ORI: BECAUSE OF stop=0 POSSIBILITY, USE POSITIVE COORDS
            return self.classySlice(self.path._reverse, -(self.stop),
                                    -(self.start), self.step)

    def __add__(self, other):
        "return merged interval spanning both self and other intervals"
        if self.path is not other.path:
            raise ValueError('incompatible intervals cannot be merged.')
        if self.start < other.start:
            start = self.start
        else:
            start = other.start
        if self.stop > other.stop:
            stop = self.stop
        else:
            stop = other.stop
        if stop == 0:
            # Have to handle the boundary case specially because of Python
            # conventions.
            stop = None
        return self.classySlice(self.path, start, stop, self.step)

    def __iadd__(self, other):
        "return merged interval spanning both self and other intervals"
        if self.path is not other.path:
            raise ValueError('incompatible intervals cannot be merged.')
        if other.start < self.start:
            self.start = other.start
        if other.stop > self.stop:
            self.stop = other.stop
        return self # iadd MUST ALWAYS RETURN self!!

    def before(self):
        'get the sequence interval before this interval'
        return self.classySlice(self.path, None, self.start)

    def after(self):
        'get the sequence interval after this interval'
        if self.stop == 0:
            raise IndexError('cannot create empty sequence interval')
        return self.classySlice(self.path, self.stop, None)

    def is_full_length(self):
        '''test whether this constitutes the whole sequence (in either
        orientation)'''
        return self == self.path

    ############################################ STRING SEQUENCE METHODS
    _complement = {'a': 't', 'c': 'g', 'g': 'c', 't': 'a', 'u': 'a', 'n': 'n',
                   'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A', 'U': 'A', 'N': 'N'}

    def reverse_complement(self, s):
        'get reverse complement of a string s'
        #return ''.join([self._complement.get(c, c) for c in s[::-1]])
        return ''.join([self._complement.get(s[i], s[i]) for i in
                        range(len(s) -1, -1, -1)])

    def seqtype(self):
        "Get the sequence type for this sequence"
        path = self.pathForward
        try: # TRY GETTING IT FROM TOP-LEVEL SEQUENCE OBJECT?
            return path._seqtype
        except AttributeError:
            try: # TRY TO GET IT FROM DB THIS SEQ IS ASSOCIATED WITH, IF ANY
                return path.db._seqtype
            except AttributeError:# GUESS IT FROM 1ST 40 LETTERS OF SEQUENCE
                path._seqtype = guess_seqtype(str(self[0:40]))
                return path._seqtype

    def __str__(self):
        '''string for this sequence interval; use reverse complement
        if necessary...'''
        if self.orientation > 0:
            return self.path.strslice(self.start, self.stop)
        else:
            s = self.path._reverse.strslice(-(self.stop), -(self.start))
            return self.reverse_complement(s)

    def __repr__(self):
        try: # USE id CONVENTION TO GET A NAME FOR THIS SEQUENCE
            id = self.pathForward.id
        except AttributeError: # OTHERWISE USE A DEFAULT, SHOWING THERE'S NO id
            id = '@NONAME'
        if self.orientation < 0: # INDICATE NEGATIVE ORIENTATION
            return '-%s[%d:%d]' % (id, -self.stop, -self.start)
        else:
            return '%s[%d:%d]' % (id, self.start, self.stop)

    def repr_dict(self):
        "Return compact dictionary representing this interval"
        try:
            id = self.path.id
        except AttributeError:
            id = self.id
        return {'id': id, 'start': self.start, 'end': self.stop,
                'ori': self.orientation}


class LengthDescriptor(object):
    'property that just returns length of object'

    def __get__(self, seq, klass):
        return len(seq)


# BASIC WRAPPER FOR A SEQUENCE.  LETS US ATTACH A NAME TO IT...
class SequenceBase(SeqPath):
    '''base sequence type assumes there will be a seq attribute
    providing sequence'''
    start = 0
    stop = LengthDescriptor()
    step = 1
    orientation = 1

    def __init__(self):
        self.path = self

    def update(self, seq):
        'change this sequence to the string <seq>'
        self.seq = seq

    def __len__(self):
        'default: get the whole self.seq and compute its length'
        return len(self.seq) # COMPUTE IT FROM THE SEQUENCE

    def strslice(self, start, stop):
        'default method assumes self.seq is a sliceable string'
        return self.seq[start:stop]


class Sequence(SequenceBase):
    'default sequence class initialized with a sequence string and ID'

    def __init__(self, s, id):
        SequenceBase.__init__(self)
        self.id = id
        self.seq = s


class SeqFilterDict(dict):
    '''stores a set of intervals, either on init or via self[ival]=junk;
    self[ival] returns intersection of ival and the overlapping
    interval in self if any; otherwise raise KeyError'''

    def __init__(self, l=[]):
        'accepts optional arg giving list of intervals'
        dict.__init__(self)
        for ival in l:
            self[ival] = None

    def __getitem__(self, k):
        try:
            ival = dict.__getitem__(self, k.path)
        except KeyError:
            raise KeyError('seq not in dict')
        result = k * ival # RETURN INTERSECTION OF IVALS
        if result is None:
            raise KeyError # PROPER WAY TO SIGNAL KEY MAPS TO NO VALUE
        return result

    def __setitem__(self, ival, junk):
        dict.__setitem__(self, ival.path, ival)

    def __iter__(self):
        return dict.itervalues(self)
##
##
## class S2SEEdgesDescriptor(object):
##     "list of interval matches as list of tuples (ival1, ival2, xform)"
##     def __get__(self, s2se, objtype):
##         return [(t.srcPath, t.destPath, t) for t in s2se.matches]


class Seq2SeqEdge(object):
    '''Maps two sequence regions onto each other, using a list
    of scalar transformations.  Can handle indels within the
    mapping.'''
    #edges = S2SEEdgesDescriptor()

    def __init__(self, msaSlice, targetPath, sourcePath=None,
                 matchIntervals=False):
        self.msaSlice = msaSlice
        self.targetPath = targetPath
        if sourcePath is not None:
            self.sourcePath = sourcePath
            self.matchIntervals = matchIntervals
        else: # NEED TO REVERSE-MAP targetPath TO FIND sourcePath
            # Mask to targetPath.
            si = msaSlice.groupByIntervals(filterList = [targetPath],
                                           mergeAll=True)
            l = msaSlice.groupBySequences(si)
            try:
                self.sourcePath = l[0][0]
            except IndexError:
                raise KeyError('target interval not in msaSlice!')
            self.matchIntervals = l[0][2]

    def items(self, mergeAll=False, **kwargs):
        'get list of (srcPath, destPath) 1:1 matches'
        if self.matchIntervals is None: # THIS IS ALREADY A 1:1 INTERVAL!
            return [(self.sourcePath, self.targetPath)]
        elif self.matchIntervals is False:
            raise ValueError('no matchIntervals information!')
        l = [] # USE STORED LIST OF 1:1 INTERVALS
        for srcStart, srcEnd, destStart, destEnd in self.matchIntervals:
            l.append((absoluteSlice(self.sourcePath, srcStart, srcEnd),
                      absoluteSlice(self.targetPath, destStart, destEnd)))
        return l

    def get_gaps(self):
        'return list of (srcIval,destIval) representing gaps / insertions'
        if self.matchIntervals is False:
            raise ValueError('no matchIntervals information!')
        elif self.matchIntervals is None or len(self.matchIntervals) < 2:
            return [] # no gaps here...
        srcLast = self.matchIntervals[0][1] # ends of 1st aligned intervals
        destLast = self.matchIntervals[0][3]
        l = []
        for t in self.matchIntervals[1:]:
            if t[0] > srcLast: # gap region
                srcIval = absoluteSlice(self.sourcePath, srcLast, t[0])
            else:
                srcIval = None
            if t[2] > destLast: # insertion region
                destIval = absoluteSlice(self.targetPath, destLast, t[2])
            else:
                destIval = None
            if srcIval is not None or destIval is not None:
                l.append((srcIval, destIval))
            srcLast = t[1] # ends of these aligned intervals
            destLast = t[3]
        return l

    def __iter__(self, sourceOnly=True, **kwargs):
        return iter([t[0] for t in self.items(sourceOnly=sourceOnly,
                                              **kwargs)])

    def length(self, mode=max):
        'get length of source vs. target interval according to mode'
        return mode(len(self.sourcePath), len(self.targetPath))

    def pIdentity(self, mode=max, trapOverflow=True):
        "calculate fractional identity for this pairwise alignment"
        nid = 0
        start1 = self.sourcePath.start
        s1 = str(self.sourcePath).upper()
        start2 = self.targetPath.start
        s2 = str(self.targetPath).upper()
        for srcPath, destPath in self.items():
            isrc = srcPath.start - start1
            idest = destPath.start - start2
            for i in xrange(len(srcPath)):
                if s1[isrc + i] == s2[idest + i]:
                    nid += 1
        x = nid / float(self.length(mode))
        if trapOverflow and x > 1.:
            raise ValueError('''pIdentity overflow due to multiple hits
                             (see docs)? To avoid this error message,
                             use trapOverflow=False option.''')
        return x

    def longestSegment(self, segment, pIdentityMin=.9, minAlignSize=1,
                       mode=max, **kwargs):
        besthit = None
        for i in xrange(len(segment)):
            ni = 0 # IDENTITY COUNT
            nm = 0 # MISMATCH COUNT
            for j in xrange(i, -1, -1):
                ni += segment[j][2]
                l = mode(segment[i][0] + segment[i][2] - segment[j][0],
                       segment[i][1] + segment[i][2] - segment[j][1])
                pIdentity = float(ni) / l
                if pIdentity >= pIdentityMin and (besthit is None or
                                                  ni + nm > besthit[4]):
                    besthit = (segment[j][0], segment[i][0] + segment[i][2],
                               segment[j][1], segment[i][1] + segment[i][2],
                               ni + nm)
                nm += segment[j][3]
        if besthit is None:
            return None
        elif besthit[4] >= minAlignSize:
            return besthit[:4]
        else:
            return None

    def conservedSegment(self, **kwargs):
        "calculate fractional identity for this pairwise alignment"
        start1 = self.sourcePath.start
        s1 = str(self.sourcePath).upper()
        start2 = self.targetPath.start
        s2 = str(self.targetPath).upper()
        i1 = None
        segment = []
        n = 0
        # Find unbroken identity segments.
        for srcPath, destPath in self.items():
            isrc = srcPath.start - start1
            idest = destPath.start - start2
            for i in xrange(len(srcPath)):
                if s1[isrc + i] == s2[idest + i]: # EXACT MATCH
                    if i1 is None: # START NEW IDENTITY-SEGMENT
                        seg1, i1 = isrc + i, isrc + i
                        seg2, i2 = idest + i, idest + i
                    elif i1 + 1 != isrc + i or i2 + 1 != idest + i:
                        # Not contiguous, break.
                        segment.append((seg1 + start1, seg2 + start2,
                                        i1 + 1 - seg1, n))
                        n = 0 # RESET MISMATCH COUNT
                        seg1, i1 = isrc + i, isrc + i
                        seg2, i2 = idest + i, idest + i
                    else:
                        i1 = isrc + i
                        i2 = idest + i
                else: # MISMATCH
                    if i1 is not None: # BREAK PREVIOUS SEGMENT
                        segment.append((seg1 + start1, seg2 + start2,
                                        i1 + 1 - seg1, n))
                        i1 = None
                        n = 0 # RESET MISMATCH COUNT
                    n += 1 # COUNT MISMATCH
        if i1 is not None:
            segment.append((seg1 + start1, seg2 + start2, i1 + 1 - seg1, n))
        return self.longestSegment(segment, **kwargs)

    def pAligned(self, mode=max, trapOverflow=True):
        'get fraction of aligned letters for this pairwise alignment'
        nid = 0
        for srcPath, destPath in self.items():
            nid += len(destPath)
        x = nid / float(self.length(mode))
        if trapOverflow and x > 1.:
            raise ValueError('''pAligned overflow due to multiple hits
                             (see docs)? To avoid this error message,
                             use trapOverflow=False option.''')
        return x


class SeqDBDescriptor(object):
    'forwards attribute requests to self.pathForward'

    def __init__(self, attr):
        self.attr = attr

    def __get__(self, obj, objtype):
        # Raises an AttributeError if None.
        return getattr(obj.pathForward, self.attr)


class SeqDBSlice(SeqPath):
    'JUST A WRAPPER FOR SCHEMA TO HANG SHADOW ATTRIBUTES ON...'
    id = SeqDBDescriptor('id')
    db = SeqDBDescriptor('db')



# CURRENTLY UNUSED

## class PathEdgeDict(dict):
##
##     def __init__(self, p):
##         self.path = p.path
##         self.pos = p.end - 1
##         if p.end < len(p.path):
##             dict.__setitem__(self, p.path[p.end], 1)
##         if hasattr(p.path, '_next') and self.pos in p.path._next:
##             dict.update(self, p.path._next[self.pos])
##
##     def __setitem__(self, k, val):
##         print 'entered PathEdgeDict.setitem'
##         if not hasattr(self.path, '_next'):
##             self.path._next = {}
##         if self.pos not in self.path._next:
##             self.path._next[self.pos] = {}
##         self.path._next[self.pos][k] = val
##         dict.__setitem__(self, k, val)


## class PathNextDescr(object):
##
##     def __init__(self, attrName='next'):
##         self.attrName = attrName
##
##     def __get__(self, obj, objtype):
##         return PathEdgeDict(obj)
##
##     def __set__(self, obj, val):
##         raise AttributeError(self.attrName + ' is read-only!')


## class LengthDescriptor(object):
##
##     def __init__(self, attr):
##         self.attr = attr
##
##     def __get__(self, obj, objtype):
##         return len(getattr(obj, self.attr))
##
##     def __set__(self, obj, val):
##         raise AttributeError(self.attr + ' is read-only!')


## def firstItem(aList):
##     if hasattr(aList, '__iter__'):
##         for i in aList:
##             return i
##     else:
##         return aList

########NEW FILE########
__FILENAME__ = sequtil

DNA_SEQTYPE=0
RNA_SEQTYPE=1
PROTEIN_SEQTYPE=2


def guess_seqtype(s):
    dna_letters='AaTtUuGgCcNn'
    ndna=0
    nU=0
    nT=0
    for l in s:
        if l in dna_letters:
            ndna += 1
        if l=='U' or l=='u':
            nU += 1
        elif l=='T' or l=='t':
            nT += 1
    ratio=ndna/float(len(s))
    if ratio>0.85:
        if nT>nU:
            return DNA_SEQTYPE
        else:
            return RNA_SEQTYPE
    else:
        return PROTEIN_SEQTYPE


seq_id_counter=0


def new_seq_id():
    global seq_id_counter
    seq_id_counter += 1
    return str(seq_id_counter-1)


def write_fasta(ofile, s, chunk=60, id=None, reformatter=None):
    "Trivial FASTA output"
    if id is None:
        try:
            id = str(s.id)
        except AttributeError:
            id = new_seq_id()

    ofile.write('>' + id + '\n')
    seq = str(s)
    if reformatter is not None: # APPLY THE DESIRED REFORMATTING
        seq = reformatter(seq)
    end = len(seq)
    pos = 0
    while 1:
        ofile.write(seq[pos:pos+chunk] + '\n')
        pos += chunk
        if pos >= end:
            break
    return id # IN CASE CALLER WANTS TEMP ID WE MAY HAVE ASSIGNED


def read_fasta(ifile):
    "iterate over id,title,seq from stream ifile"
    id = None
    isEmpty = True
    for line in ifile:
        if '>' == line[0]:
            if id is not None and len(seq) > 0:
                yield id, title, seq
                isEmpty = False
            id = line[1:].split()[0]
            title = line[len(id)+2:]
            seq = ''
        elif id is not None: # READ SEQUENCE
            for word in line.split(): # GET RID OF WHITESPACE
                seq += word
    if id is not None and len(seq) > 0:
        yield id, title, seq
    elif isEmpty:
        raise IOError('no readable sequence in FASTA file!')


def read_fasta_one_line(ifile): # @CTB deprecated; remove
    "read a single sequence line, return id,title,seq"
    id = None
    seq = ''
    while True:
        line = ifile.readline(1024) # READ AT MOST 1KB
        if line == '': # EOF
            break
        elif '>' == line[0]:
            id = line[1:].split()[0]
            title = line[len(id)+2:]
        elif id is not None: # READ SEQUENCE
            for word in line.split(): # GET RID OF WHITESPACE
                seq += word
            if len(seq) > 0:
                return id, title, seq
    raise IOError('no readable sequence in FASTA file!')


def read_fasta_lengths(ifile):
    "Generate sequence ID,length from stream ifile"
    id = None
    seqLength = 0
    isEmpty = True
    for line in ifile:
        if '>' == line[0]:
            if id is not None and seqLength > 0:
                yield id, seqLength
                isEmpty = False
            id = line[1:].split()[0]
            seqLength = 0
        elif id is not None: # READ SEQUENCE
            for word in line.split(): # GET RID OF WHITESPACE
                seqLength += len(word)
    if id is not None and seqLength > 0:
        yield id, seqLength
    elif isEmpty:
        raise IOError('no readable sequence in FASTA file!')


class AATranslation(object):
    'customizable translation class'
    geneticCode = dict(TTY='F', TTR='L', TCN='S', TAY='Y', TGY='C', TGG='W',
                       CTN='L', CCN='P', CAY='H', CAR='Q', CGN='R',
                       ATY='I', ATA='I', ATG='M', ACN='T', AAY='N', AAR='K',
                       AGY='S', AGR='R',
                       GTN='V', GCN='A', GAY='D', GAR='E', GGN='G',
                       TAR='*', TGA='*')

    def __init__(self):
        'initialize our translation dictionary by applying N,Y,R codes'
        geneticCode = self.geneticCode.copy()
        for codon, aa in self.geneticCode.items():
            if codon[2] == 'N':
                geneticCode[codon[:2]+'A'] = aa
                geneticCode[codon[:2]+'T'] = aa
                geneticCode[codon[:2]+'G'] = aa
                geneticCode[codon[:2]+'C'] = aa
            elif codon[2] == 'Y':
                geneticCode[codon[:2]+'T'] = aa
                geneticCode[codon[:2]+'C'] = aa
            elif codon[2] == 'R':
                geneticCode[codon[:2]+'A'] = aa
                geneticCode[codon[:2]+'G'] = aa
        self.geneticCode = geneticCode

    def __call__(self, s):
        'translate nucleotide string s to amino acid string'
        s = s.upper()
        s = s.replace('U', 'T')
        l = []
        for i in range(0, len(s), 3):
            try:
                l.append(self.geneticCode[s[i:i+3]])
            except KeyError:
                l.append('X') # uninterpretable
        return ''.join(l)

translate_orf = AATranslation() # default translation function

########NEW FILE########
__FILENAME__ = sqlgraph


from __future__ import generators
from mapping import *
from sequence import SequenceBase, DNA_SEQTYPE, RNA_SEQTYPE, PROTEIN_SEQTYPE
import types
from classutil import methodFactory, standard_getstate,\
     override_rich_cmp, generate_items, get_bound_subclass, standard_setstate,\
     get_valid_path, standard_invert, RecentValueDictionary, read_only_error,\
     SourceFileName, split_kwargs
import os
import platform
import UserDict
import warnings
import logger


class TupleDescriptor(object):
    'return tuple entry corresponding to named attribute'

    def __init__(self, db, attr):
        self.icol = db._attrSQL(attr, columnNumber=True) # index in the tuple

    def __get__(self, obj, klass):
        return obj._data[self.icol]

    def __set__(self, obj, val):
        raise AttributeError('this database is read-only!')


class TupleIDDescriptor(TupleDescriptor):

    def __set__(self, obj, val):
        raise AttributeError('''You cannot change obj.id directly.
        Instead, use db[newID] = obj''')


class TupleDescriptorRW(TupleDescriptor):
    'read-write interface to named attribute'

    def __init__(self, db, attr):
        self.attr = attr
        self.icol = db._attrSQL(attr, columnNumber=True) # index in the tuple
        self.attrSQL = db._attrSQL(attr, sqlColumn=True) # SQL column name

    def __set__(self, obj, val):
        obj.db._update(obj.id, self.attrSQL, val) # AND UPDATE THE DATABASE
        obj.save_local(self.attr, val, self.icol)


class SQLDescriptor(object):
    'return attribute value by querying the database'

    def __init__(self, db, attr):
        self.selectSQL = db._attrSQL(attr) # SQL expression for this attr

    def __get__(self, obj, klass):
        return obj._select(self.selectSQL)

    def __set__(self, obj, val):
        raise AttributeError('this database is read-only!')


class SQLDescriptorRW(SQLDescriptor):
    'writeable proxy to corresponding column in the database'

    def __set__(self, obj, val):
        obj.db._update(obj.id, self.selectSQL, val) #just update the database


class ReadOnlyDescriptor(object):
    'enforce read-only policy, e.g. for ID attribute'

    def __init__(self, db, attr):
        self.attr = '_'+attr

    def __get__(self, obj, klass):
        return getattr(obj, self.attr)

    def __set__(self, obj, val):
        raise AttributeError('attribute %s is read-only!' % self.attr)


def select_from_row(row, what):
    "return value from SQL expression applied to this row"
    sql, params = row.db._format_query('select %s from %s where %s=%%s limit 2'
                                       % (what, row.db.name,
                                          row.db.primary_key), (row.id, ))
    row.db.cursor.execute(sql, params)
    t = row.db.cursor.fetchmany(2) # get at most two rows
    if len(t) != 1:
        raise KeyError('%s[%s].%s not found, or not unique'
                       % (row.db.name, str(row.id), what))
    return t[0][0] #return the single field we requested


def init_row_subclass(cls, db):
    'add descriptors for db attributes'
    try: # check itemClass compatibility with db.__class__
        if not isinstance(db, cls._tableclass):
            raise ValueError('''Your itemClass %s is not compatible
with your database class %s.
With this itemClass you must use %s as your base class instead.'''
                             % (cls, db.__class__, cls._tableclass))
    except AttributeError: # if no _tableclass, no need to do anything
        pass
    for attr in db.data: # bind all database columns
        if attr == 'id': # handle ID attribute specially
            setattr(cls, attr, cls._idDescriptor(db, attr))
            continue
        try: # treat as interface to our stored tuple
            setattr(cls, attr, cls._columnDescriptor(db, attr))
        except AttributeError: # treat as SQL expression
            setattr(cls, attr, cls._sqlDescriptor(db, attr))

def dir_row(self):
    """get list of column names as our attributes """
    return self.db.data.keys()

class TupleO(object):
    """Provides attribute interface to a database tuple.
    Storing the data as a tuple instead of a standard Python object
    (which is stored using __dict__) uses about five-fold less
    memory and is also much faster (the tuples returned from the
    DB API fetch are simply referenced by the TupleO, with no
    need to copy their individual values into __dict__).

    This class follows the 'subclass binding' pattern, which
    means that instead of using __getattr__ to process all
    attribute requests (which is un-modular and leads to all
    sorts of trouble), we follow Python's new model for
    customizing attribute access, namely Descriptors.
    We use classutil.get_bound_subclass() to automatically
    create a subclass of this class, calling its _init_subclass()
    class method to add all the descriptors needed for the
    database table to which it is bound.

    See the Pygr Developer Guide section of the docs for a
    complete discussion of the subclass binding pattern."""
    _columnDescriptor = TupleDescriptor
    _idDescriptor = TupleIDDescriptor
    _sqlDescriptor = SQLDescriptor
    _init_subclass = classmethod(init_row_subclass)
    _select = select_from_row
    __dir__ = dir_row

    def __init__(self, data):
        self._data = data # save our data tuple


def insert_and_cache_id(self, l, **kwargs):
    'insert tuple into db and cache its rowID on self'
    self.db._insert(l) # save to database
    try:
        rowID = kwargs['id']  # use the ID supplied by user
    except KeyError:
        rowID = self.db.get_insert_id() # get auto-inc ID value
    self.cache_id(rowID) # cache this ID on self


class TupleORW(TupleO):
    'read-write version of TupleO'
    _columnDescriptor = TupleDescriptorRW
    insert_and_cache_id = insert_and_cache_id

    def __init__(self, data, newRow=False, **kwargs):
        if not newRow: # just cache data from the database
            self._data = data
            return
        self._data = self.db.tuple_from_dict(kwargs) # convert to tuple
        self.insert_and_cache_id(self._data, **kwargs)

    def cache_id(self, row_id):
        self.save_local('id', row_id, self.db._attrSQL('id', columnNumber=True))

    def save_local(self, attr, val, icol):
        try:
            self._data[icol] = val # FINALLY UPDATE OUR LOCAL CACHE
        except TypeError: # TUPLE CAN'T STORE NEW VALUE, SO USE A LIST
            self._data = list(self._data)
            self._data[icol] = val # FINALLY UPDATE OUR LOCAL CACHE


TupleO._RWClass = TupleORW # record this as writeable interface class


class ColumnDescriptor(object):
    'read-write interface to column in a database, cached in obj.__dict__'

    def __init__(self, db, attr, readOnly = False):
        self.attr = attr
        # Map attr to SQL column name.
        self.col = db._attrSQL(attr, sqlColumn=True)
        self.db = db
        if readOnly:
            self.__class__ = self._readOnlyClass

    def __get__(self, obj, objtype):
        try:
            return obj.__dict__[self.attr]
        except KeyError: # NOT IN CACHE.  TRY TO GET IT FROM DATABASE
            if self.col==self.db.primary_key:
                raise AttributeError
            self.db._select('where %s=%%s' % self.db.primary_key, (obj.id, ),
                            self.col)
            l = self.db.cursor.fetchall()
            if len(l)!=1:
                raise AttributeError('db row not found or not unique!')
            obj.__dict__[self.attr] = l[0][0] # UPDATE THE CACHE
            return l[0][0]

    def __set__(self, obj, val):
        if not hasattr(obj, '_localOnly'): # ONLY CACHE, DON'T SAVE TO DATABASE
            self.db._update(obj.id, self.col, val) # UPDATE THE DATABASE
        obj.__dict__[self.attr] = val # UPDATE THE CACHE
##         try:
##             m = self.consequences
##         except AttributeError:
##             return
##         m(obj, val) # GENERATE CONSEQUENCES
##     def bind_consequences(self, f):
##         'make function f be run as consequences method whenever value is set'
##         import new
##         self.consequences = new.instancemethod(f, self, self.__class__)


class ReadOnlyColumnDesc(ColumnDescriptor):

    def __set__(self, obj, val):
        raise AttributeError('The ID of a database object is not writeable.')
ColumnDescriptor._readOnlyClass = ReadOnlyColumnDesc


class SQLRow(object):
    """Provide transparent interface to a row in the database: attribute access
       will be mapped to SELECT of the appropriate column, but data is not
       cached on this object.
    """
    _columnDescriptor = _sqlDescriptor = SQLDescriptor
    _idDescriptor = ReadOnlyDescriptor
    _init_subclass = classmethod(init_row_subclass)
    _select = select_from_row
    __dir__ = dir_row

    def __init__(self, rowID):
        self._id = rowID


class SQLRowRW(SQLRow):
    'read-write version of SQLRow'
    _columnDescriptor = SQLDescriptorRW
    insert_and_cache_id = insert_and_cache_id

    def __init__(self, rowID, newRow=False, **kwargs):
        if not newRow: # just cache data from the database
            return self.cache_id(rowID)
        l = self.db.tuple_from_dict(kwargs) # convert to tuple
        self.insert_and_cache_id(l, **kwargs)

    def cache_id(self, rowID):
        self._id = rowID


SQLRow._RWClass = SQLRowRW


def list_to_dict(names, values):
    'return dictionary of those named args that are present in values[]'
    d = {}
    for i, v in enumerate(values):
        try:
            d[names[i]] = v
        except IndexError:
            break
    return d


def get_name_cursor(name=None, **kwargs):
    '''get table name and cursor by parsing name or using configFile.
    If neither provided, will try to get via your MySQL config file.
    If connect is None, will use MySQLdb.connect()'''
    if name is not None:
        argList = name.split() # TREAT AS WS-SEPARATED LIST
        if len(argList) > 1:
            name = argList[0] # USE 1ST ARG AS TABLE NAME
            argnames = ('host', 'user', 'passwd') # READ ARGS IN THIS ORDER
            kwargs = kwargs.copy() # a copy we can overwrite
            kwargs.update(list_to_dict(argnames, argList[1:]))
    serverInfo = DBServerInfo(**kwargs)
    return name, serverInfo.cursor(), serverInfo


def mysql_connect(connect=None, configFile=None, useStreaming=False, **args):
    """return connection and cursor objects, using .my.cnf if necessary"""
    kwargs = args.copy() # a copy we can modify
    if 'user' not in kwargs and configFile is None: #Find where config file is
        osname = platform.system()
        if osname in('Microsoft', 'Windows'): # Machine is a Windows box
            paths = []
            try: # handle case where WINDIR not defined by Windows...
                windir = os.environ['WINDIR']
                paths += [(windir, 'my.ini'), (windir, 'my.cnf')]
            except KeyError:
                pass
            try:
                sysdrv = os.environ['SYSTEMDRIVE']
                paths += [(sysdrv, os.path.sep + 'my.ini'),
                          (sysdrv, os.path.sep + 'my.cnf')]
            except KeyError:
                pass
            if len(paths) > 0:
                configFile = get_valid_path(*paths)
        else: # treat as normal platform with home directories
            configFile = os.path.join(os.path.expanduser('~'), '.my.cnf')

    # allows for a local mysql local configuration file to be read
    # from the current directory
    configFile = configFile or os.path.join(os.getcwd(), 'mysql.cnf')

    if configFile and os.path.exists(configFile):
        kwargs['read_default_file'] = configFile
        connect = None # force it to use MySQLdb
    if connect is None:
        import MySQLdb
        connect = MySQLdb.connect
        kwargs['compress'] = True
    if useStreaming:  # use server side cursors for scalable result sets
        try:
            from MySQLdb import cursors
            kwargs['cursorclass'] = cursors.SSCursor
        except (ImportError, AttributeError):
            pass
    conn = connect(**kwargs)
    cursor = conn.cursor()
    return conn, cursor


_mysqlMacros = dict(IGNORE='ignore', REPLACE='replace',
                    AUTO_INCREMENT='AUTO_INCREMENT', SUBSTRING='substring',
                    SUBSTR_FROM='FROM', SUBSTR_FOR='FOR')


def mysql_table_schema(self, analyzeSchema=True):
    'retrieve table schema from a MySQL database, save on self'
    import MySQLdb
    self._format_query = SQLFormatDict(MySQLdb.paramstyle, _mysqlMacros)
    if not analyzeSchema:
        return
    self.clear_schema() # reset settings and dictionaries
    self.cursor.execute('describe %s' % self.name) # get info about columns
    columns = self.cursor.fetchall()
    self.cursor.execute('select * from %s limit 1' % self.name) # descriptions
    for icol, c in enumerate(columns):
        field = c[0]
        self.columnName.append(field) # list of columns in same order as table
        if c[3] == "PRI": # record as primary key
            if self.primary_key is None:
                self.primary_key = field
            else:
                try:
                    self.primary_key.append(field)
                except AttributeError:
                    self.primary_key = [self.primary_key, field]
            if c[1][:3].lower() == 'int':
                self.usesIntID = True
            else:
                self.usesIntID = False
        elif c[3] == "MUL":
            self.indexed[field] = icol
        self.description[field] = self.cursor.description[icol]
        self.columnType[field] = c[1] # SQL COLUMN TYPE


_sqliteMacros = dict(IGNORE='or ignore', REPLACE='insert or replace',
                     AUTO_INCREMENT='', SUBSTRING='substr',
                    SUBSTR_FROM=',', SUBSTR_FOR=',')


def import_sqlite():
    'import sqlite3 (for Python 2.5+) or pysqlite2 for earlier Python versions'
    try:
        import sqlite3 as sqlite
    except ImportError:
        from pysqlite2 import dbapi2 as sqlite
    return sqlite


def sqlite_table_schema(self, analyzeSchema=True):
    'retrieve table schema from a sqlite3 database, save on self'
    sqlite = import_sqlite()
    self._format_query = SQLFormatDict(sqlite.paramstyle, _sqliteMacros)
    if not analyzeSchema:
        return
    self.clear_schema() # reset settings and dictionaries
    self.cursor.execute('PRAGMA table_info("%s")' % self.name)
    columns = self.cursor.fetchall()
    self.cursor.execute('select * from %s limit 1' % self.name) # descriptions
    for icol, c in enumerate(columns):
        field = c[1]
        self.columnName.append(field) # list of columns in same order as table
        self.description[field] = self.cursor.description[icol]
        self.columnType[field] = c[2] # SQL COLUMN TYPE
    # Get primary key / unique indexes.
    self.cursor.execute('select name from sqlite_master where tbl_name="%s" \
                        and type="index" and sql is null' % self.name)
    for indexname in self.cursor.fetchall(): # search indexes for primary key
        self.cursor.execute('PRAGMA index_info("%s")' % indexname)
        l = self.cursor.fetchall() # get list of columns in this index
        if len(l) == 1: # assume 1st single-column unique index is primary key!
            self.primary_key = l[0][2]
            break # done searching for primary key!
    if self.primary_key is None:
        # Grrr, INTEGER PRIMARY KEY handled differently.
        self.cursor.execute('select sql from sqlite_master where \
                            tbl_name="%s" and type="table"' % self.name)
        sql = self.cursor.fetchall()[0][0]
        for columnSQL in sql[sql.index('(') + 1:].split(','):
            if 'primary key' in columnSQL.lower(): # must be the primary key!
                col = columnSQL.split()[0] # get column name
                if col in self.columnType:
                    self.primary_key = col
                    break # done searching for primary key!
                else:
                    raise ValueError('unknown primary key %s in table %s'
                                     % (col, self.name))
    if self.primary_key is not None: # check its type
        if self.columnType[self.primary_key] == 'int' or \
               self.columnType[self.primary_key] == 'integer':
            self.usesIntID = True
        else:
            self.usesIntID = False


class SQLFormatDict(object):
    '''Perform SQL keyword replacements for maintaining compatibility across
    a wide range of SQL backends.  Uses Python dict-based string format
    function to do simple string replacements, and also to convert
    params list to the paramstyle required for this interface.
    Create by passing a dict of macros and the db-api paramstyle:
    sfd = SQLFormatDict("qmark", substitutionDict)

    Then transform queries+params as follows; input should be "format" style:
    sql,params = sfd("select * from foo where id=%s and val=%s", (myID,myVal))
    cursor.execute(sql, params)
    '''
    _paramFormats = dict(pyformat='%%(%d)s', numeric=':%d', named=':%d',
                         qmark='(ignore)', format='(ignore)')

    def __init__(self, paramstyle, substitutionDict={}):
        self.substitutionDict = substitutionDict.copy()
        self.paramstyle = paramstyle
        self.paramFormat = self._paramFormats[paramstyle]
        self.makeDict = (paramstyle == 'pyformat' or paramstyle == 'named')
        if paramstyle == 'qmark': # handle these as simple substitution
            self.substitutionDict['?'] = '?'
        elif paramstyle == 'format':
            self.substitutionDict['?'] = '%s'

    def __getitem__(self, k):
        'apply correct substitution for this SQL interface'
        try:
            return self.substitutionDict[k] # apply our substitutions
        except KeyError:
            pass
        if k == '?': # sequential parameter
            s = self.paramFormat % self.iparam
            self.iparam += 1 # advance to the next parameter
            return s
        raise KeyError('unknown macro: %s' % k)

    def __call__(self, sql, paramList):
        'returns corrected sql,params for this interface'
        self.iparam = 1 # DB-ABI param indexing begins at 1
        sql = sql.replace('%s', '%(?)s') # convert format into pyformat
        s = sql % self # apply all %(x)s replacements in sql
        if self.makeDict: # construct a params dict
            paramDict = {}
            for i, param in enumerate(paramList):
                # i + 1 because DB-ABI parameter indexing begins at 1
                paramDict[str(i + 1)] = param
            return s, paramDict
        else: # just return the original params list
            return s, paramList


def get_table_schema(self, analyzeSchema=True):
    'run the right schema function based on type of db server connection'
    try:
        modname = self.cursor.__class__.__module__
    except AttributeError:
        raise ValueError('no cursor object or module information!')
    try:
        schema_func = self._schemaModuleDict[modname]
    except KeyError:
        raise KeyError('''unknown db module: %s. Use _schemaModuleDict
        attribute to supply a method for obtaining table schema
        for this module''' % modname)
    schema_func(self, analyzeSchema) # run the schema function


_schemaModuleDict = {'MySQLdb.cursors': mysql_table_schema,
                     'pysqlite2.dbapi2': sqlite_table_schema,
                     'sqlite3': sqlite_table_schema}


class SQLTableBase(object, UserDict.DictMixin):
    "Store information about an SQL table as dict keyed by primary key"
    _schemaModuleDict = _schemaModuleDict # default module list
    get_table_schema = get_table_schema

    def __init__(self, name, cursor=None, itemClass=None, attrAlias=None,
                 clusterKey=None, createTable=None, graph=None, maxCache=None,
                 arraysize=1024, itemSliceClass=None, dropIfExists=False,
                 serverInfo=None, autoGC=True, orderBy=None,
                 writeable=False, iterSQL=None, iterColumns=None,
                 primaryKey=None, allowNonUniqueID=False, **kwargs):
        if autoGC: # automatically garbage collect unused objects
            self._weakValueDict = RecentValueDictionary(autoGC) # object cache
        else:
            self._weakValueDict = {}
        self.autoGC = autoGC
        self.orderBy = orderBy
        if orderBy and serverInfo and serverInfo._serverType == 'mysql':
            if iterSQL and iterColumns: # both required for mysql!
                self.iterSQL, self.iterColumns = iterSQL, iterColumns
            else:
                raise ValueError('For MySQL tables with orderBy, you MUST \
                                 specify iterSQL and iterColumns as well!')

        self.writeable = writeable
        if cursor is None:
            if serverInfo is not None: # get cursor from serverInfo
                cursor = serverInfo.cursor()
            else: # try to read connection info from name or config file
                name, cursor, serverInfo = get_name_cursor(name, **kwargs)
        else:
            warnings.warn("The cursor argument is deprecated. Use serverInfo \
                          instead!", DeprecationWarning, stacklevel=2)
        self.cursor = cursor
        if createTable is not None: # RUN COMMAND TO CREATE THIS TABLE
            if dropIfExists: # get rid of any existing table
                cursor.execute('drop table if exists ' + name)
            self.get_table_schema(False) # check dbtype, init _format_query
            sql, params = self._format_query(createTable, ()) # apply macros
            cursor.execute(sql) # create the table
        self.name = name
        if graph is not None:
            self.graph = graph
        if maxCache is not None:
            self.maxCache = maxCache
        if arraysize is not None:
            self.arraysize = arraysize
            cursor.arraysize = arraysize
        self.get_table_schema() # get schema of columns to serve as attrs
        if primaryKey is not None:
            self.primary_key = primaryKey
            self.primaryKey = primaryKey
        self.allowNonUniqueID = allowNonUniqueID
        self.data = {} # map of all attributes, including aliases
        for icol, field in enumerate(self.columnName):
            self.data[field] = icol # 1st add mappings to columns
        try:
            self.data['id'] = self.data[self.primary_key]
        except (KeyError, TypeError):
            pass
        if hasattr(self, '_attr_alias'):
            # Apply attribute aliases for this class.
            self.addAttrAlias(False, **self._attr_alias)
        if attrAlias is not None: # ADD ATTRIBUTE ALIASES
            self.attrAlias = attrAlias # RECORD FOR PICKLING PURPOSES
            self.data.update(attrAlias)
        self.objclass(itemClass) # NEED TO SUBCLASS OUR ITEM CLASS
        if itemSliceClass is not None:
            self.itemSliceClass = itemSliceClass
            # Need to subclass itemSliceClass.
            get_bound_subclass(self, 'itemSliceClass', self.name)
        if clusterKey is not None:
            self.clusterKey = clusterKey
        if serverInfo is not None:
            self.serverInfo = serverInfo

    def __len__(self):
        self._select(selectCols = 'count(*)')
        return self.cursor.fetchone()[0]

    def __hash__(self):
        return id(self)

    def __cmp__(self, other):
        'only match self and no other!'
        if self is other:
            return 0
        else:
            return cmp(id(self), id(other))
    _pickleAttrs = dict(name=0, clusterKey=0, maxCache=0, arraysize=0,
                        attrAlias=0, serverInfo=0, autoGC=0, orderBy=0,
                        writeable=0, iterSQL=0, iterColumns=0, primaryKey=0)
    __getstate__ = standard_getstate

    def __setstate__(self, state):
        # default cursor provisioning by worldbase is deprecated!
        ## if 'serverInfo' not in state: # hmm, no address for db server?
        ##     try: # SEE IF WE CAN GET CURSOR DIRECTLY FROM RESOURCE DATABASE
        ##         from Data import getResource
        ##         state['cursor'] = getResource.getTableCursor(state['name'])
        ##     except ImportError:
        ##         pass # FAILED, SO TRY TO GET A CURSOR IN THE USUAL WAYS...
        self.__init__(**state)

    def __repr__(self):
        return '<SQL table ' + self.name + '>'

    def clear_schema(self):
        'reset all schema information for this table'
        self.description={}
        self.columnName = []
        self.columnType = {}
        self.usesIntID = None
        self.primary_key = None
        self.indexed = {}

    def _attrSQL(self, attr, sqlColumn=False, columnNumber=False):
        "Translate python attribute name to appropriate SQL expression"
        try: # MAKE SURE THIS ATTRIBUTE CAN BE MAPPED TO DATABASE EXPRESSION
            field = self.data[attr]
        except KeyError:
            raise AttributeError('attribute %s not a valid column \
                                 or alias in %s' % (attr, self.name))
        if sqlColumn: # ENSURE THAT THIS TRULY MAPS TO A COLUMN NAME IN THE DB
            try: # CHECK IF field IS COLUMN NUMBER
                return self.columnName[field] # RETURN SQL COLUMN NAME
            except TypeError:
                try:
                    # Check if field is SQL column name, return it if so.
                    return self.columnName[self.data[field]]
                except (KeyError, TypeError):
                    raise AttributeError('attribute %s does not map to an SQL \
                                         column in %s' % (attr, self.name))
        if columnNumber:
            try: # CHECK IF field IS A COLUMN NUMBER
                return field + 0 # ONLY RETURN AN INTEGER
            except TypeError:
                try: # CHECK IF field IS ITSELF THE SQL COLUMN NAME
                    return self.data[field] + 0 # ONLY RETURN AN INTEGER
                except (KeyError, TypeError):
                    raise AttributeError('attribute %s does not map to a SQL \
column!' % attr)
        if isinstance(field, types.StringType):
            # Use aliased expression for database select instead of attr.
            attr = field
        elif attr == 'id':
            attr = self.primary_key
        return attr

    def addAttrAlias(self, saveToPickle=True, **kwargs):
        """Add new attributes as aliases of existing attributes.
           They can be specified either as named args:
           t.addAttrAlias(newattr=oldattr)
           or by passing a dictionary kwargs whose keys are newattr
           and values are oldattr:
           t.addAttrAlias(**kwargs)
           saveToPickle=True forces these aliases to be saved if object
           is pickled.
        """
        if saveToPickle:
            self.attrAlias.update(kwargs)
        for key, val in kwargs.items():
            try: # 1st CHECK WHETHER val IS AN EXISTING COLUMN / ALIAS
                self.data[val] + 0 # CHECK WHETHER val MAPS TO A COLUMN NUMBER
                # Yes, val is an actual SQL column name, so save it directly.
                raise KeyError
            except TypeError: # val IS ITSELF AN ALIAS
                self.data[key] = self.data[val] # SO MAP TO WHAT IT MAPS TO
            except KeyError: # TREAT AS ALIAS TO SQL EXPRESSION
                self.data[key] = val

    def objclass(self, oclass=None):
        """Create class representing a row in this table
        by subclassing oclass, adding data"""
        if oclass is not None: # use this as our base itemClass
            self.itemClass = oclass
        if self.writeable:
            # Use its writeable version.
            self.itemClass = self.itemClass._RWClass
        # Bind itemClass.
        oclass = get_bound_subclass(self, 'itemClass', self.name,
                                    subclassArgs=dict(db=self))

    def _select(self, whereClause='', params=(), selectCols='t1.*',
                cursor=None, orderBy='', limit=''):
        'execute the specified query but do not fetch'
        sql, params = self._format_query('select %s from %s t1 %s %s %s'
                            % (selectCols, self.name, whereClause, orderBy,
                               limit), params)
        if cursor is None:
            self.cursor.execute(sql, params)
        else:
            cursor.execute(sql, params)

    def select(self, whereClause, params=None, oclass=None, selectCols='t1.*'):
        "Generate the list of objects that satisfy the database SELECT"
        if oclass is None:
            oclass = self.itemClass
        self._select(whereClause, params, selectCols)
        l = self.cursor.fetchall()
        for t in l:
            yield self.cacheItem(t, oclass)

    def query(self, **kwargs):
        'query for intersection of all specified kwargs, returned as iterator'
        criteria = []
        params = []
        for k, v in kwargs.items(): # CONSTRUCT THE LIST OF WHERE CLAUSES
            if v is None: # CONVERT TO SQL NULL TEST
                criteria.append('%s IS NULL' % self._attrSQL(k))
            else: # TEST FOR EQUALITY
                criteria.append('%s=%%s' % self._attrSQL(k))
                params.append(v)
        return self.select('where ' + ' and '.join(criteria), params)

    def _update(self, row_id, col, val):
        'update a single field in the specified row to the specified value'
        sql, params = self._format_query('update %s set %s=%%s where %s=%%s'
                                         % (self.name, col, self.primary_key),
                                         (val, row_id))
        self.cursor.execute(sql, params)

    def getID(self, t):
        try:
            return t[self.data['id']] # GET ID FROM TUPLE
        except TypeError: # treat as alias
            return t[self.data[self.data['id']]]

    def cacheItem(self, t, oclass):
        'get obj from cache if possible, or construct from tuple'
        try:
            id = self.getID(t)
        except KeyError: # NO PRIMARY KEY?  IGNORE THE CACHE.
            return oclass(t)
        try: # IF ALREADY LOADED IN OUR DICTIONARY, JUST RETURN THAT ENTRY
            return self._weakValueDict[id]
        except KeyError:
            pass
        o = oclass(t)
        self._weakValueDict[id] = o   # CACHE THIS ITEM IN OUR DICTIONARY
        return o

    def cache_items(self, rows, oclass=None):
        if oclass is None:
            oclass = self.itemClass
        for t in rows:
            yield self.cacheItem(t, oclass)

    def foreignKey(self, attr, k):
        'get iterator for objects with specified foreign key value'
        return self.select('where %s=%%s' % attr, (k, ))

    def limit_cache(self):
        'APPLY maxCache LIMIT TO CACHE SIZE'
        try:
            if self.maxCache<len(self._weakValueDict):
                self._weakValueDict.clear()
        except AttributeError:
            pass

    def get_new_cursor(self):
        """Return a new cursor object, or None if not possible """
        try:
            new_cursor = self.serverInfo.new_cursor
        except AttributeError:
            return None
        return new_cursor(self.arraysize)

    def generic_iterator(self, cursor=None, fetch_f=None, cache_f=None,
                         map_f=iter, cursorHolder=None):
        """generic iterator that runs fetch, cache and map functions.
        cursorHolder is used only to keep a ref in this function's locals,
        so that if it is prematurely terminated (by deleting its
        iterator), cursorHolder.__del__() will close the cursor."""
        if fetch_f is None: # JUST USE CURSOR'S PREFERRED CHUNK SIZE
            if cursor is None:
                fetch_f = self.cursor.fetchmany
            else:  # isolate this iter from other queries
                fetch_f = cursor.fetchmany
        if cache_f is None:
            cache_f = self.cache_items
        while True:
            self.limit_cache()
            rows = fetch_f() # FETCH THE NEXT SET OF ROWS
            if len(rows) == 0: # NO MORE DATA SO ALL DONE
                break
            for v in map_f(cache_f(rows)): # CACHE AND GENERATE RESULTS
                yield v

    def tuple_from_dict(self, d):
        'transform kwarg dict into tuple for storing in database'
        l = [None] * len(self.description) # DEFAULT COLUMN VALUES ARE NULL
        for col, icol in self.data.items():
            try:
                l[icol] = d[col]
            except (KeyError, TypeError):
                pass
        return l

    def tuple_from_obj(self, obj):
        'transform object attributes into tuple for storing in database'
        l = [None] * len(self.description) # DEFAULT COLUMN VALUES ARE NULL
        for col, icol in self.data.items():
            try:
                l[icol] = getattr(obj, col)
            except (AttributeError, TypeError):
                pass
        return l

    def _insert(self, l):
        '''insert tuple into the database.  Note this uses the MySQL
        extension REPLACE, which overwrites any duplicate key.'''
        s = '%(REPLACE)s into ' + self.name + ' values (' \
            + ','.join(['%s']*len(l)) + ')'
        sql, params = self._format_query(s, l)
        self.cursor.execute(sql, params)

    def insert(self, obj):
        '''insert new row by transforming obj to tuple of values'''
        l = self.tuple_from_obj(obj)
        self._insert(l)

    def get_insert_id(self):
        'get the primary key value for the last INSERT'
        try: # ATTEMPT TO GET ASSIGNED ID FROM DB
            auto_id = self.cursor.lastrowid
        except AttributeError: # CURSOR DOESN'T SUPPORT lastrowid
            raise NotImplementedError('''your db lacks lastrowid support?''')
        if auto_id is None:
            raise ValueError('lastrowid is None so cannot get ID from INSERT!')
        return auto_id

    def new(self, **kwargs):
        'return a new record with the assigned attributes, added to DB'
        if not self.writeable:
            raise ValueError('this database is read only!')
        obj = self.itemClass(None, newRow=True, **kwargs) # saves itself to db
        self._weakValueDict[obj.id] = obj # AND SAVE TO OUR LOCAL DICT CACHE
        return obj

    def clear_cache(self):
        'empty the cache'
        self._weakValueDict.clear()

    def __delitem__(self, k):
        if not self.writeable:
            raise ValueError('this database is read only!')
        sql, params = self._format_query('delete from %s where %s=%%s'
                                         % (self.name, self.primary_key),
                                         (k, ))
        self.cursor.execute(sql, params)
        try:
            del self._weakValueDict[k]
        except KeyError:
            pass


def getKeys(self, queryOption='', selectCols=None):
    'uses db select; does not force load'
    if selectCols is None:
        selectCols=self.primary_key
    if queryOption=='' and self.orderBy is not None:
        queryOption = self.orderBy # apply default ordering
    self.cursor.execute('select %s from %s %s'
                        % (selectCols, self.name, queryOption))
    # Get all at once, since other calls may reuse this cursor.
    return [t[0] for t in self.cursor.fetchall()]


def iter_keys(self, selectCols=None, orderBy='', map_f=iter,
              cache_f=lambda x: [t[0] for t in x], get_f=None, **kwargs):
    'guarantee correct iteration insulated from other queries'
    if selectCols is None:
        selectCols = self.primary_key
    if orderBy == '' and self.orderBy is not None:
        orderBy = self.orderBy # apply default ordering
    cursor = self.get_new_cursor()
    if cursor: # got our own cursor, guaranteeing query isolation
        if hasattr(self.serverInfo, 'iter_keys') \
           and self.serverInfo.custom_iter_keys:
            # use custom iter_keys() method from serverInfo
            return self.serverInfo.iter_keys(self, cursor,
                                             selectCols=selectCols,
                                             map_f=map_f, orderBy=orderBy,
                                             cache_f=cache_f, **kwargs)
        else:
            self._select(cursor=cursor, selectCols=selectCols,
                         orderBy=orderBy, **kwargs)
            return self.generic_iterator(cursor=cursor, cache_f=cache_f,
                                         map_f=map_f,
                                         cursorHolder=CursorCloser(cursor))
    else: # must pre-fetch all keys to ensure query isolation
        if get_f is not None:
            return iter(get_f())
        else:
            return iter(self.keys())


class SQLTable(SQLTableBase):
    """Provide on-the-fly access to rows in the database, caching
    the results in dict"""
    itemClass = TupleO # our default itemClass; constructor can override
    keys = getKeys
    __iter__ = iter_keys

    def load(self, oclass=None):
        "Load all data from the table"
        try: # IF ALREADY LOADED, NO NEED TO DO ANYTHING
            return self._isLoaded
        except AttributeError:
            pass
        if oclass is None:
            oclass = self.itemClass
        self.cursor.execute('select * from %s' % self.name)
        l = self.cursor.fetchall()
        self._weakValueDict = {} # just store the whole dataset in memory
        for t in l:
            self.cacheItem(t, oclass) # CACHE IT IN LOCAL DICTIONARY
        self._isLoaded = True # MARK THIS CONTAINER AS FULLY LOADED

    def __getitem__(self, k): # FIRST TRY LOCAL INDEX, THEN TRY DATABASE
        try:
            return self._weakValueDict[k] # DIRECTLY RETURN CACHED VALUE
        except KeyError: # NOT FOUND, SO TRY THE DATABASE
            sql, params = self._format_query('select * from %s where %s=%%s \
                                             limit 2' % (self.name,
                                                         self.primary_key),
                                             (k, ))
            self.cursor.execute(sql, params)
            l = self.cursor.fetchmany(2) # get at most 2 rows
            if len(l) == 0:
                raise KeyError('%s not found in %s' % (str(k), self.name))
            if len(l) > 1 and not self.allowNonUniqueID:
                raise KeyError('%s not unique in %s' % (str(k), self.name))
            self.limit_cache()
            # Cache it in local dictionary.
            return self.cacheItem(l[0], self.itemClass)

    def __setitem__(self, k, v):
        if not self.writeable:
            raise ValueError('this database is read only!')
        try:
            if v.db is not self:
                raise AttributeError
        except AttributeError:
            raise ValueError('object not bound to itemClass for this db!')
        try:
            oldID = v.id
            if oldID is None:
                raise AttributeError
        except AttributeError:
            pass
        else: # delete row with old ID
            del self[v.id]
        v.cache_id(k) # cache the new ID on the object
        self.insert(v) # SAVE TO THE RELATIONAL DB SERVER
        self._weakValueDict[k] = v   # CACHE THIS ITEM IN OUR DICTIONARY

    def items(self):
        'forces load of entire table into memory'
        self.load()
        return [(k, self[k]) for k in self] # apply orderBy rules...

    def iteritems(self):
        'uses arraysize / maxCache and fetchmany() to manage data transfer'
        return iter_keys(self, selectCols='*', cache_f=None,
                         map_f=generate_items, get_f=self.items)

    def values(self):
        'forces load of entire table into memory'
        self.load()
        return [self[k] for k in self] # apply orderBy rules...

    def itervalues(self):
        'uses arraysize / maxCache and fetchmany() to manage data transfer'
        return iter_keys(self, selectCols='*', cache_f=None, get_f=self.values)


def getClusterKeys(self, queryOption=''):
    'uses db select; does not force load'
    self.cursor.execute('select distinct %s from %s %s'
                        % (self.clusterKey, self.name, queryOption))
    # Get all at once, since other calls may reuse this cursor.
    return [t[0] for t in self.cursor.fetchall()]


class SQLTableClustered(SQLTable):
    '''use clusterKey to load a whole cluster of rows at once,
       specifically, all rows that share the same clusterKey value.'''

    def __init__(self, *args, **kwargs):
        kwargs = kwargs.copy() # get a copy we can alter
        kwargs['autoGC'] = False # don't use WeakValueDictionary
        SQLTable.__init__(self, *args, **kwargs)
        if not self.orderBy: # add default ordering by clusterKey
            self.orderBy = 'ORDER BY %s,%s' % (self.clusterKey,
                                               self.primary_key)
            self.iterColumns = (self.clusterKey, self.clusterKey,
                                self.primary_key)
            self.iterSQL = 'WHERE %s>%%s or (%s=%%s and %s>%%s)' \
                           % self.iterColumns

    def clusterkeys(self):
        return getClusterKeys(self, 'order by %s' % self.clusterKey)

    def __getitem__(self, k):
        try:
            return self._weakValueDict[k] # DIRECTLY RETURN CACHED VALUE
        except KeyError: # NOT FOUND, SO TRY THE DATABASE
            sql, params = self._format_query('select t2.* from %s t1,%s t2 \
                                             where t1.%s=%%s and t1.%s=t2.%s'
                                             % (self.name, self.name,
                                                self.primary_key,
                                                self.clusterKey,
                                                self.clusterKey), (k, ))
            self.cursor.execute(sql, params)
            l = self.cursor.fetchall()
            self.limit_cache()
            for t in l: # LOAD THE ENTIRE CLUSTER INTO OUR LOCAL CACHE
                self.cacheItem(t, self.itemClass)
            return self._weakValueDict[k] # should be in cache, if row k exists

    def itercluster(self, cluster_id):
        'iterate over all items from the specified cluster'
        self.limit_cache()
        return self.select('where %s=%%s' % self.clusterKey, (cluster_id, ))


class SQLForeignRelation(object):
    'mapping based on matching a foreign key in an SQL table'

    def __init__(self, table, keyName):
        self.table = table
        self.keyName = keyName

    def __getitem__(self, k):
        'get list of objects o with getattr(o,keyName)==k.id'
        l = []
        for o in self.table.select('where %s=%%s' % self.keyName, (k.id, )):
            l.append(o)
        if len(l) == 0:
            raise KeyError('%s not found in %s' % (str(k), self.name))
        return l


class SQLTableNoCache(SQLTableBase):
    '''Provide on-the-fly access to rows in the database;
    values are simply an object interface (SQLRow) to back-end db query.
    Row data are not stored locally, but always accessed by querying the db'''
    itemClass = SQLRow # DEFAULT OBJECT CLASS FOR ROWS...
    keys = getKeys
    __iter__ = iter_keys

    def getID(self, t):
        return t[0] # GET ID FROM TUPLE

    def select(self, whereClause, params):
        return SQLTableBase.select(self, whereClause, params, self.oclass,
                                   self._attrSQL('id'))

    def __getitem__(self, k): # FIRST TRY LOCAL INDEX, THEN TRY DATABASE
        try:
            return self._weakValueDict[k] # DIRECTLY RETURN CACHED VALUE
        except KeyError: # NOT FOUND, SO TRY THE DATABASE
            self._select('where %s=%%s' % self.primary_key, (k, ),
                         self.primary_key)
            t = self.cursor.fetchmany(2)
            if len(t) == 0:
                raise KeyError('id %s non-existent' % k)
            if len(t) > 1 and not self.allowNonUniqueID:
                raise KeyError('id %s not unique' % k)
            o = self.itemClass(k) # create obj referencing this ID
            self._weakValueDict[k] = o # cache the SQLRow object
            return o

    def __setitem__(self, k, v):
        if not self.writeable:
            raise ValueError('this database is read only!')
        try:
            if v.db is not self:
                raise AttributeError
        except AttributeError:
            raise ValueError('object not bound to itemClass for this db!')
        try:
            del self[k] # delete row with new ID if any
        except KeyError:
            pass
        try:
            del self._weakValueDict[v.id] # delete from old cache location
        except KeyError:
            pass
        self._update(v.id, self.primary_key, k) # just change its ID in db
        v.cache_id(k) # change the cached ID value
        self._weakValueDict[k] = v # assign to new cache location

    def addAttrAlias(self, **kwargs):
        self.data.update(kwargs) # ALIAS KEYS TO EXPRESSION VALUES


# SQLRow is for non-caching table interface.
SQLRow._tableclass = SQLTableNoCache


class SQLTableMultiNoCache(SQLTableBase):
    "Trivial on-the-fly access for table with key that returns multiple rows"
    itemClass = TupleO # default itemClass; constructor can override
    _distinct_key = 'id' # DEFAULT COLUMN TO USE AS KEY

    def __init__(self, *args, **kwargs):
        SQLTableBase.__init__(self, *args, **kwargs)
        self.distinct_key = self._attrSQL(self._distinct_key)
        if not self.orderBy:
            self.orderBy = 'GROUP BY %s ORDER BY %s' % (self.distinct_key,
                                                        self.distinct_key)
            self.iterSQL = 'WHERE %s>%%s' % self.distinct_key
            self.iterColumns = (self.distinct_key, )

    def keys(self):
        return getKeys(self, selectCols=self.distinct_key)

    def __iter__(self):
        return iter_keys(self, selectCols=self.distinct_key)

    def __getitem__(self, id):
        sql, params = self._format_query('select * from %s where %s=%%s'
                                         % (self.name,
                                            self._attrSQL(self._distinct_key)),
                                         (id, ))
        self.cursor.execute(sql, params)
        # Prefetch all rows, since cursor may be reused.
        l = self.cursor.fetchall()
        for row in l:
            yield self.itemClass(row)

    def addAttrAlias(self, **kwargs):
        self.data.update(kwargs) # ALIAS KEYS TO EXPRESSION VALUES


class SQLEdges(SQLTableMultiNoCache):
    '''provide iterator over edges as (source, target, edge)
       and getitem[edge] --> [(source,target),...]'''
    _distinct_key = 'edge_id'
    _pickleAttrs = SQLTableMultiNoCache._pickleAttrs.copy()
    _pickleAttrs.update(dict(graph=0))

    def keys(self):
        self.cursor.execute('select %s,%s,%s from %s where %s is not null \
                            order by %s,%s' % (self._attrSQL('source_id'),
                                               self._attrSQL('target_id'),
                                               self._attrSQL('edge_id'),
                                               self.name,
                                               self._attrSQL('target_id'),
                                               self._attrSQL('source_id'),
                                               self._attrSQL('target_id')))
        l = [] # PREFETCH ALL ROWS, SINCE CURSOR MAY BE REUSED
        for source_id, target_id, edge_id in self.cursor.fetchall():
            l.append((self.graph.unpack_source(source_id),
                      self.graph.unpack_target(target_id),
                      self.graph.unpack_edge(edge_id)))
        return l

    __call__ = keys

    def __iter__(self):
        return iter(self.keys())

    def __getitem__(self, edge):
        sql, params = self._format_query('select %s,%s from %s where %s=%%s'
                                         % (self._attrSQL('source_id'),
                                            self._attrSQL('target_id'),
                                            self.name,
                                            self._attrSQL(self._distinct_key)),
                                         (self.graph.pack_edge(edge), ))
        self.cursor.execute(sql, params)
        l = [] # PREFETCH ALL ROWS, SINCE CURSOR MAY BE REUSED
        for source_id, target_id in self.cursor.fetchall():
            l.append((self.graph.unpack_source(source_id),
                      self.graph.unpack_target(target_id)))
        return l


class SQLEdgeDict(object):
    '2nd level graph interface to SQL database'

    def __init__(self, fromNode, table):
        self.fromNode = fromNode
        self.table = table
        if not hasattr(self.table, 'allowMissingNodes'):
            sql, params = self.table._format_query('select %s from %s where \
                                                   %s=%%s limit 1'
                                                   % (self.table.sourceSQL,
                                                      self.table.name,
                                                      self.table.sourceSQL),
                                                   (self.fromNode, ))
            self.table.cursor.execute(sql, params)
            if len(self.table.cursor.fetchall())<1:
                raise KeyError('node not in graph!')

    def __getitem__(self, target):
        sql, params = self.table._format_query('select %s from %s where \
                                               %s=%%s and %s=%%s limit 2'
                                               % (self.table.edgeSQL,
                                                  self.table.name,
                                                  self.table.sourceSQL,
                                                  self.table.targetSQL),
                                               (self.fromNode,
                                               self.table.pack_target(target)))
        self.table.cursor.execute(sql, params)
        l = self.table.cursor.fetchmany(2) # get at most two rows
        if len(l) != 1:
            raise KeyError('either no edge from source to target \
                           or not unique!')
        try:
            return self.table.unpack_edge(l[0][0]) # RETURN EDGE
        except IndexError:
            raise KeyError('no edge from node to target')

    def __setitem__(self, target, edge):
        sql, params = self.table._format_query('replace into %s values \
                                               (%%s,%%s,%%s)'
                                               % self.table.name,
                                               (self.fromNode,
                                                self.table.pack_target(target),
                                                self.table.pack_edge(edge)))
        self.table.cursor.execute(sql, params)
        if not hasattr(self.table, 'sourceDB') or \
           (hasattr(self.table, 'targetDB') and
            self.table.sourceDB is self.table.targetDB):
            self.table += target # ADD AS NODE TO GRAPH

    def __iadd__(self, target):
        self[target] = None
        return self # iadd MUST RETURN self!

    def __delitem__(self, target):
        sql, params = self.table._format_query('delete from %s where %s=%%s \
                                               and %s=%%s'
                                               % (self.table.name,
                                                  self.table.sourceSQL,
                                                  self.table.targetSQL),
                                               (self.fromNode,
                                               self.table.pack_target(target)))
        self.table.cursor.execute(sql, params)
        if self.table.cursor.rowcount < 1: # no rows deleted?
            raise KeyError('no edge from node to target')

    def iterator_query(self):
        sql, params = self.table._format_query('select %s,%s from %s where \
                                               %s=%%s and %s is not null'
                                               % (self.table.targetSQL,
                                                  self.table.edgeSQL,
                                                  self.table.name,
                                                  self.table.sourceSQL,
                                                  self.table.targetSQL),
                                               (self.fromNode, ))
        self.table.cursor.execute(sql, params)
        return self.table.cursor.fetchall()

    def keys(self):
        return [self.table.unpack_target(target_id)
                for target_id, edge_id in self.iterator_query()]

    def values(self):
        return [self.table.unpack_edge(edge_id)
                for target_id, edge_id in self.iterator_query()]

    def edges(self):
        return [(self.table.unpack_source(self.fromNode),
                 self.table.unpack_target(target_id),
                 self.table.unpack_edge(edge_id))
                for target_id, edge_id in self.iterator_query()]

    def items(self):
        return [(self.table.unpack_target(target_id),
                 self.table.unpack_edge(edge_id))
                for target_id, edge_id in self.iterator_query()]

    def __iter__(self):
        return iter(self.keys())

    def itervalues(self):
        return iter(self.values())

    def iteritems(self):
        return iter(self.items())

    def __len__(self):
        return len(self.keys())

    __cmp__ = graph_cmp


class SQLEdgelessDict(SQLEdgeDict):
    'for SQLGraph tables that lack edge_id column'

    def __getitem__(self, target):
        sql, params = self.table._format_query('select %s from %s where \
                                               %s=%%s and %s=%%s limit 2'
                                               % (self.table.targetSQL,
                                                  self.table.name,
                                                  self.table.sourceSQL,
                                                  self.table.targetSQL),
                                               (self.fromNode,
                                               self.table.pack_target(target)))
        self.table.cursor.execute(sql, params)
        l = self.table.cursor.fetchmany(2)
        if len(l) != 1:
            raise KeyError('either no edge from source to target \
                           or not unique!')
        return None # no edge info!

    def iterator_query(self):
        sql, params = self.table._format_query('select %s from %s where \
                                               %s=%%s and %s is not null'
                                               % (self.table.targetSQL,
                                                  self.table.name,
                                                  self.table.sourceSQL,
                                                  self.table.targetSQL),
                                               (self.fromNode, ))
        self.table.cursor.execute(sql, params)
        return [(t[0], None) for t in self.table.cursor.fetchall()]


SQLEdgeDict._edgelessClass = SQLEdgelessDict


class SQLGraphEdgeDescriptor(object):
    'provide an SQLEdges interface on demand'

    def __get__(self, obj, objtype):
        try:
            attrAlias = obj.attrAlias.copy()
        except AttributeError:
            return SQLEdges(obj.name, obj.cursor, graph=obj)
        else:
            return SQLEdges(obj.name, obj.cursor, attrAlias=attrAlias,
                            graph=obj)


def getColumnTypes(createTable, attrAlias={}, defaultColumnType='int',
                  columnAttrs=('source', 'target', 'edge'), **kwargs):
    'return list of [(colname, coltype), ...] for source, target, edge'
    l = []
    for attr in columnAttrs:
        try:
            attrName = attrAlias[attr + '_id']
        except KeyError:
            attrName = attr + '_id'
        try: # SEE IF USER SPECIFIED A DESIRED TYPE
            l.append((attrName, createTable[attr + '_id']))
            continue
        except (KeyError, TypeError):
            pass
        try: # get type info from primary key for that database
            db = kwargs[attr + 'DB']
            if db is None:
                raise KeyError # FORCE IT TO USE DEFAULT TYPE
        except KeyError:
            pass
        else: # INFER THE COLUMN TYPE FROM THE ASSOCIATED DATABASE KEYS...
            it = iter(db)
            try: # GET ONE IDENTIFIER FROM THE DATABASE
                k = it.next()
            except StopIteration:
                # Table is empty, read the SQL type from db.
                try:
                    l.append((attrName, db.columnType[db.primary_key]))
                    continue
                except AttributeError:
                    pass
            else: # GET THE TYPE FROM THIS IDENTIFIER
                if isinstance(k, int) or isinstance(k, long):
                    l.append((attrName, 'int'))
                    continue
                elif isinstance(k, str):
                    l.append((attrName, 'varchar(32)'))
                    continue
                else:
                    raise ValueError('SQLGraph node/edge must be int or str!')
        l.append((attrName, defaultColumnType))
        logger.warn('no type info found for %s, so using default: %s'
                    % (attrName, defaultColumnType))
    return l


class SQLGraph(SQLTableMultiNoCache):
    '''provide a graph interface via a SQL table.  Key capabilities are:
       - setitem with an empty dictionary: a dummy operation
       - getitem with a key that exists: return a placeholder
       - setitem with non empty placeholder: again a dummy operation
       EXAMPLE TABLE SCHEMA:
       create table mygraph (source_id int not null,target_id int,edge_id int,
              unique(source_id,target_id));
       '''
    _distinct_key = 'source_id'
    _pickleAttrs = SQLTableMultiNoCache._pickleAttrs.copy()
    _pickleAttrs.update(dict(sourceDB=0, targetDB=0, edgeDB=0,
                             allowMissingNodes=0))
    _edgeClass = SQLEdgeDict

    def __init__(self, name, *l, **kwargs):
        graphArgs, tableArgs = split_kwargs(kwargs,
                    ('attrAlias', 'defaultColumnType', 'columnAttrs',
                     'sourceDB', 'targetDB', 'edgeDB', 'simpleKeys',
                     'unpack_edge', 'edgeDictClass', 'graph'))
        if 'createTable' in kwargs: # CREATE A SCHEMA FOR THIS TABLE
            c = getColumnTypes(**kwargs)
            tableArgs['createTable'] = \
              'create table %s (%s %s not null,%s %s,%s %s,unique(%s,%s))' \
              % (name, c[0][0], c[0][1], c[1][0], c[1][1], c[2][0], c[2][1],
                 c[0][0], c[1][0])
        try:
            self.allowMissingNodes = kwargs['allowMissingNodes']
        except KeyError:
            pass
        SQLTableMultiNoCache.__init__(self, name, *l, **tableArgs)
        self.sourceSQL = self._attrSQL('source_id')
        self.targetSQL = self._attrSQL('target_id')
        try:
            self.edgeSQL = self._attrSQL('edge_id')
        except AttributeError:
            self.edgeSQL = None
            self._edgeClass = self._edgeClass._edgelessClass
        save_graph_db_refs(self, **kwargs)

    def __getitem__(self, k):
        return self._edgeClass(self.pack_source(k), self)

    def __iadd__(self, k):
        sql, params = self._format_query('delete from %s where %s=%%s and %s \
                                         is null' % (self.name, self.sourceSQL,
                                                     self.targetSQL),
                                         (self.pack_source(k), ))
        self.cursor.execute(sql, params)
        sql, params = self._format_query('insert %%(IGNORE)s into %s values \
                                         (%%s,NULL,NULL)' % self.name,
                                         (self.pack_source(k), ))
        self.cursor.execute(sql, params)
        return self # iadd MUST RETURN SELF!

    def __isub__(self, k):
        sql, params = self._format_query('delete from %s where %s=%%s'
                                         % (self.name, self.sourceSQL),
                                         (self.pack_source(k), ))
        self.cursor.execute(sql, params)
        if self.cursor.rowcount == 0:
            raise KeyError('node not found in graph')
        return self # iadd MUST RETURN SELF!

    __setitem__ = graph_setitem

    def __contains__(self, k):
        sql, params = self._format_query('select * from %s where %s=%%s \
                                         limit 1' % (self.name,
                                                     self.sourceSQL),
                                         (self.pack_source(k), ))
        self.cursor.execute(sql, params)
        l = self.cursor.fetchmany(2)
        return len(l) > 0

    def __invert__(self):
        'get an interface to the inverse graph mapping'
        try: # CACHED
            return self._inverse
        except AttributeError: # CONSTRUCT INTERFACE TO INVERSE MAPPING
            attrAlias = dict(source_id=self.targetSQL, # SWAP SOURCE & TARGET
                             target_id=self.sourceSQL,
                             edge_id=self.edgeSQL)
            if self.edgeSQL is None: # no edge interface
                del attrAlias['edge_id']
            self._inverse = SQLGraph(self.name, self.cursor,
                                     attrAlias=attrAlias,
                                     **graph_db_inverse_refs(self))
            self._inverse._inverse = self
            return self._inverse

    def __iter__(self):
        for k in SQLTableMultiNoCache.__iter__(self):
            yield self.unpack_source(k)

    def iteritems(self):
        for k in SQLTableMultiNoCache.__iter__(self):
            yield (self.unpack_source(k), self._edgeClass(k, self))

    def itervalues(self):
        for k in SQLTableMultiNoCache.__iter__(self):
            yield self._edgeClass(k, self)

    def keys(self):
        return [self.unpack_source(k) for k in SQLTableMultiNoCache.keys(self)]

    def values(self):
        return list(self.itervalues())

    def items(self):
        return list(self.iteritems())

    edges=SQLGraphEdgeDescriptor()
    update = update_graph

    def __len__(self):
        'get number of source nodes in graph'
        self.cursor.execute('select count(distinct %s) from %s'
                            % (self.sourceSQL, self.name))
        return self.cursor.fetchone()[0]

    __cmp__ = graph_cmp
    override_rich_cmp(locals()) # MUST OVERRIDE __eq__ ETC. TO USE OUR __cmp__!

##     def __cmp__(self, other):
##         node = ()
##         n = 0
##         d = None
##         it = iter(self.edges)
##         while True:
##             try:
##                 source, target, edge = it.next()
##             except StopIteration:
##                 source = None
##             if source != node:
##                 if d is not None:
##                     diff = cmp(n_target, len(d))
##                     if diff != 0:
##                         return diff
##                 if source is None:
##                     break
##                 node = source
##                 n += 1 # COUNT SOURCE NODES
##                 n_target = 0
##                 try:
##                     d = other[node]
##                 except KeyError:
##                     return 1
##             try:
##                 diff = cmp(edge, d[target])
##             except KeyError:
##                 return 1
##             if diff != 0:
##                 return diff
##             n_target += 1 # COUNT TARGET NODES FOR THIS SOURCE
##         return cmp(n, len(other))

    add_standard_packing_methods(locals())  ############ PACK / UNPACK METHODS


class SQLIDGraph(SQLGraph):
    add_trivial_packing_methods(locals())

SQLGraph._IDGraphClass = SQLIDGraph


class SQLEdgeDictClustered(dict):
    'simple cache for 2nd level dictionary of target_id:edge_id'

    def __init__(self, g, fromNode):
        self.g = g
        self.fromNode = fromNode
        dict.__init__(self)

    def __iadd__(self, l):
        for target_id, edge_id in l:
            dict.__setitem__(self, target_id, edge_id)
        return self # iadd MUST RETURN SELF!


class SQLEdgesClusteredDescr(object):

    def __get__(self, obj, objtype):
        e = SQLEdgesClustered(obj.table, obj.edge_id, obj.source_id,
                              obj.target_id, graph=obj,
                              **graph_db_inverse_refs(obj, True))
        for source_id, d in obj.d.iteritems(): # COPY EDGE CACHE
            e.load([(edge_id, source_id, target_id)
                    for (target_id, edge_id) in d.iteritems()])
        return e


class SQLGraphClustered(object):
    'SQL graph with clustered caching -- loads an entire cluster at a time'
    _edgeDictClass = SQLEdgeDictClustered

    def __init__(self, table, source_id='source_id', target_id='target_id',
                 edge_id='edge_id', clusterKey=None, **kwargs):
        import types
        if isinstance(table, types.StringType): # CREATE THE TABLE INTERFACE
            if clusterKey is None:
                raise ValueError('you must provide a clusterKey argument!')
            if 'createTable' in kwargs: # CREATE A SCHEMA FOR THIS TABLE
                c = getColumnTypes(attrAlias=dict(source_id=source_id,
                                                  target_id=target_id,
                                                  edge_id=edge_id), **kwargs)
                kwargs['createTable'] = 'create table %s (%s %s not null,%s \
                        %s,%s %s,unique(%s,%s))' % (table, c[0][0], c[0][1],
                                                    c[1][0], c[1][1], c[2][0],
                                                    c[2][1], c[0][0], c[1][0])
            table = SQLTableClustered(table, clusterKey=clusterKey, **kwargs)
        self.table = table
        self.source_id = source_id
        self.target_id = target_id
        self.edge_id = edge_id
        self.d = {}
        save_graph_db_refs(self, **kwargs)

    _pickleAttrs = dict(table=0, source_id=0, target_id=0, edge_id=0,
                        sourceDB=0, targetDB=0, edgeDB=0)

    def __getstate__(self):
        state = standard_getstate(self)
        state['d'] = {} # UNPICKLE SHOULD RESTORE GRAPH WITH EMPTY CACHE
        return state

    def __getitem__(self, k):
        'get edgeDict for source node k, from cache or by loading its cluster'
        try: # GET DIRECTLY FROM CACHE
            return self.d[k]
        except KeyError:
            if hasattr(self, '_isLoaded'):
                raise # ENTIRE GRAPH LOADED, SO k REALLY NOT IN THIS GRAPH
        # HAVE TO LOAD THE ENTIRE CLUSTER CONTAINING THIS NODE
        sql, params = self.table._format_query('select t2.%s,t2.%s,t2.%s \
               from %s t1,%s t2 where t1.%s=%%s and t1.%s=t2.%s group by t2.%s'
                                  % (self.source_id, self.target_id,
                                     self.edge_id, self.table.name,
                                     self.table.name, self.source_id,
                                     self.table.clusterKey,
                                     self.table.clusterKey,
                                     self.table.primary_key),
                                  (self.pack_source(k), ))
        self.table.cursor.execute(sql, params)
        self.load(self.table.cursor.fetchall()) # CACHE THIS CLUSTER
        return self.d[k] # RETURN EDGE DICT FOR THIS NODE

    def load(self, l=None, unpack=True):
        'load the specified rows (or all, if None provided) into local cache'
        if l is None:
            try: # IF ALREADY LOADED, NO NEED TO DO ANYTHING
                return self._isLoaded
            except AttributeError:
                pass
            self.table.cursor.execute('select %s,%s,%s from %s'
                                      % (self.source_id, self.target_id,
                                         self.edge_id, self.table.name))
            l = self.table.cursor.fetchall()
            self._isLoaded = True
            # Clear our cache as load() will replicate everything.
            self.d.clear()
        for source, target, edge in l: # SAVE TO OUR CACHE
            if unpack:
                source = self.unpack_source(source)
                target = self.unpack_target(target)
                edge = self.unpack_edge(edge)
            try:
                self.d[source] += [(target, edge)]
            except KeyError:
                d = self._edgeDictClass(self, source)
                d += [(target, edge)]
                self.d[source] = d

    def __invert__(self):
        'interface to reverse graph mapping'
        try:
            return self._inverse # INVERSE MAP ALREADY EXISTS
        except AttributeError:
            pass
        # JUST CREATE INTERFACE WITH SWAPPED TARGET & SOURCE
        self._inverse = SQLGraphClustered(self.table, self.target_id,
                                          self.source_id, self.edge_id,
                                          **graph_db_inverse_refs(self))
        self._inverse._inverse = self
        for source, d in self.d.iteritems(): # INVERT OUR CACHE
            self._inverse.load([(target, source, edge)
                                for (target, edge) in d.iteritems()],
                               unpack=False)
        return self._inverse
    edges=SQLEdgesClusteredDescr() # CONSTRUCT EDGE INTERFACE ON DEMAND
    update = update_graph
    add_standard_packing_methods(locals())  ############ PACK / UNPACK METHODS

    def __iter__(self): ################# ITERATORS
        'uses db select; does not force load'
        return iter(self.keys())

    def keys(self):
        'uses db select; does not force load'
        self.table.cursor.execute('select distinct(%s) from %s'
                                  % (self.source_id, self.table.name))
        return [self.unpack_source(t[0])
                for t in self.table.cursor.fetchall()]

    methodFactory(['iteritems', 'items', 'itervalues', 'values'],
                  'lambda self: (self.load(), self.d.%s())[1]', locals())

    def __contains__(self, k):
        try:
            x = self[k]
            return True
        except KeyError:
            return False


class SQLIDGraphClustered(SQLGraphClustered):
    add_trivial_packing_methods(locals())

SQLGraphClustered._IDGraphClass = SQLIDGraphClustered


class SQLEdgesClustered(SQLGraphClustered):
    'edges interface for SQLGraphClustered'
    _edgeDictClass = list
    _pickleAttrs = SQLGraphClustered._pickleAttrs.copy()
    _pickleAttrs.update(dict(graph=0))

    def keys(self):
        self.load()
        result = []
        for edge_id, l in self.d.iteritems():
            for source_id, target_id in l:
                result.append((self.graph.unpack_source(source_id),
                               self.graph.unpack_target(target_id),
                               self.graph.unpack_edge(edge_id)))
        return result


class ForeignKeyInverse(object):
    'map each key to a single value according to its foreign key'

    def __init__(self, g):
        self.g = g

    def __getitem__(self, obj):
        self.check_obj(obj)
        source_id = getattr(obj, self.g.keyColumn)
        if source_id is None:
            return None
        return self.g.sourceDB[source_id]

    def __setitem__(self, obj, source):
        self.check_obj(obj)
        if source is not None:
            # Ensures performing all the right caching operations.
            self.g[source][obj] = None
        else: # DELETE PRE-EXISTING EDGE IF PRESENT
            if not hasattr(obj, '_localOnly'):
                # Only cache, don't save to database.
                old_source = self[obj]
                if old_source is not None:
                    del self.g[old_source][obj]

    def check_obj(self, obj):
        'raise KeyError if obj not from this db'
        try:
            if obj.db is not self.g.targetDB:
                raise AttributeError
        except AttributeError:
            raise KeyError('key is not from targetDB of this graph!')

    def __contains__(self, obj):
        try:
            self.check_obj(obj)
            return True
        except KeyError:
            return False

    def __iter__(self):
        return self.g.targetDB.itervalues()

    def keys(self):
        return self.g.targetDB.values()

    def iteritems(self):
        for obj in self:
            source_id = getattr(obj, self.g.keyColumn)
            if source_id is None:
                yield obj, None
            else:
                yield obj, self.g.sourceDB[source_id]

    def items(self):
        return list(self.iteritems())

    def itervalues(self):
        for obj, val in self.iteritems():
            yield val

    def values(self):
        return list(self.itervalues())

    def __invert__(self):
        return self.g


class ForeignKeyEdge(dict):
    '''edge interface to a foreign key in an SQL table.
Caches dict of target nodes in itself; provides dict interface.
Adds or deletes edges by setting foreign key values in the table'''

    def __init__(self, g, k):
        dict.__init__(self)
        self.g = g
        self.src = k
        for v in g.targetDB.select('where %s=%%s' % g.keyColumn, (k.id, )):
            dict.__setitem__(self, v, None) # SAVE IN CACHE

    def __setitem__(self, dest, v):
        if not hasattr(dest, 'db') or dest.db is not self.g.targetDB:
            raise KeyError('dest is not in the targetDB bound to this graph!')
        if v is not None:
            raise ValueError('sorry,this graph cannot store edge information!')
        if not hasattr(dest, '_localOnly'):
            # Only cache, don't save to database.
            old_source = self.g._inverse[dest] # CHECK FOR PRE-EXISTING EDGE
            if old_source is not None: # REMOVE OLD EDGE FROM CACHE
                dict.__delitem__(self.g[old_source], dest)
        #self.g.targetDB._update(dest.id, self.g.keyColumn, self.src.id) # SAVE TO DB
        setattr(dest, self.g.keyColumn, self.src.id) # SAVE TO DB ATTRIBUTE
        dict.__setitem__(self, dest, None) # SAVE IN CACHE

    def __delitem__(self, dest):
        #self.g.targetDB._update(dest.id, self.g.keyColumn, None) # REMOVE FOREIGN KEY VALUE
        setattr(dest, self.g.keyColumn, None) # SAVE TO DB ATTRIBUTE
        dict.__delitem__(self, dest) # REMOVE FROM CACHE


class ForeignKeyGraph(object, UserDict.DictMixin):
    '''graph interface to a foreign key in an SQL table
Caches dict of target nodes in itself; provides dict interface.
    '''

    def __init__(self, sourceDB, targetDB, keyColumn, autoGC=True, **kwargs):
        '''sourceDB is any database of source nodes;
        targetDB must be an SQL database of target nodes;
        keyColumn is the foreign key column name in targetDB
        for looking up sourceDB IDs.'''
        if autoGC: # automatically garbage collect unused objects
            self._weakValueDict = RecentValueDictionary(autoGC) # object cache
        else:
            self._weakValueDict = {}
        self.autoGC = autoGC
        self.sourceDB = sourceDB
        self.targetDB = targetDB
        self.keyColumn = keyColumn
        self._inverse = ForeignKeyInverse(self)

    _pickleAttrs = dict(sourceDB=0, targetDB=0, keyColumn=0, autoGC=0)
    __getstate__ = standard_getstate ########### SUPPORT FOR PICKLING
    __setstate__ = standard_setstate

    def _inverse_schema(self):
        '''Provide custom schema rule for inverting this graph...
        Just use keyColumn!'''
        return dict(invert=True, uniqueMapping=True)

    def __getitem__(self, k):
        if not hasattr(k, 'db') or k.db is not self.sourceDB:
            raise KeyError('object is not in the sourceDB bound \
                           to this graph!')
        try:
            return self._weakValueDict[k.id] # get from cache
        except KeyError:
            pass
        d = ForeignKeyEdge(self, k)
        self._weakValueDict[k.id] = d # save in cache
        return d

    def __setitem__(self, k, v):
        raise KeyError('''do not save as g[k]=v.  Instead follow a graph
interface: g[src]+=dest, or g[src][dest]=None (no edge info allowed)''')

    def __delitem__(self, k):
        raise KeyError('''Instead of del g[k], follow a graph
interface: del g[src][dest]''')

    def keys(self):
        return self.sourceDB.values()

    __invert__ = standard_invert


def describeDBTables(name, cursor, idDict):
    """
    Get table info about database <name> via <cursor>, and store primary keys
    in idDict, along with a list of the tables each key indexes.
    """
    cursor.execute('use %s' % name)
    cursor.execute('show tables')
    tables = {}
    l = [c[0] for c in cursor.fetchall()]
    for t in l:
        tname = name + '.' + t
        o = SQLTable(tname, cursor)
        tables[tname] = o
        for f in o.description:
            if f == o.primary_key:
                idDict.setdefault(f, []).append(o)
            elif f[-3:] == '_id' and f not in idDict:
                idDict[f] = []
    return tables


def indexIDs(tables, idDict=None):
    "Get an index of primary keys in the <tables> dictionary."
    if idDict == None:
        idDict = {}
    for o in tables.values():
        if o.primary_key:
            # Maintain a list of tables with this primary key.
            if o.primary_key not in idDict:
                idDict[o.primary_key] = []
            idDict[o.primary_key].append(o)
        for f in o.description:
            if f[-3:] == '_id' and f not in idDict:
                idDict[f] = []
    return idDict


def suffixSubset(tables, suffix):
    "Filter table index for those matching a specific suffix"
    subset = {}
    for name, t in tables.items():
        if name.endswith(suffix):
            subset[name] = t
    return subset


PRIMARY_KEY=1


def graphDBTables(tables, idDict):
    g = dictgraph()
    for t in tables.values():
        for f in t.description:
            if f == t.primary_key:
                edgeInfo = PRIMARY_KEY
            else:
                edgeInfo = None
            g.setEdge(f, t, edgeInfo)
            g.setEdge(t, f, edgeInfo)
    return g


SQLTypeTranslation = {types.StringType: 'varchar(32)',
                      types.IntType: 'int',
                      types.FloatType: 'float'}


def createTableFromRepr(rows, tableName, cursor, typeTranslation=None,
                        optionalDict=None, indexDict=()):
    """Save rows into SQL tableName using cursor, with optional
       translations of columns to specific SQL types (specified
       by typeTranslation dict).
       - optionDict can specify columns that are allowed to be NULL.
       - indexDict can specify columns that must be indexed; columns
       whose names end in _id will be indexed by default.
       - rows must be an iterator which in turn returns dictionaries,
       each representing a tuple of values (indexed by their column
       names).
    """
    try:
        row = rows.next() # GET 1ST ROW TO EXTRACT COLUMN INFO
    except StopIteration:
        return # IF rows EMPTY, NO NEED TO SAVE ANYTHING, SO JUST RETURN
    try:
        createTableFromRow(cursor, tableName, row, typeTranslation,
                           optionalDict, indexDict)
    except:
        pass
    storeRow(cursor, tableName, row) # SAVE OUR FIRST ROW
    for row in rows: # NOW SAVE ALL THE ROWS
        storeRow(cursor, tableName, row)


def createTableFromRow(cursor, tableName, row, typeTranslation=None,
                        optionalDict=None, indexDict=()):
    create_defs = []
    for col, val in row.items(): # PREPARE SQL TYPES FOR COLUMNS
        coltype = None
        if typeTranslation != None and col in typeTranslation:
            coltype = typeTranslation[col] # USER-SUPPLIED TRANSLATION
        elif type(val) in SQLTypeTranslation:
            coltype = SQLTypeTranslation[type(val)]
        else: # SEARCH FOR A COMPATIBLE TYPE
            for t in SQLTypeTranslation:
                if isinstance(val, t):
                    coltype = SQLTypeTranslation[t]
                    break
        if coltype == None:
            raise TypeError("Don't know SQL type to use for %s" % col)
        create_def = '%s %s' % (col, coltype)
        if optionalDict == None or col not in optionalDict:
            create_def += ' not null'
        create_defs.append(create_def)
    for col in row: # CREATE INDEXES FOR ID COLUMNS
        if col[-3:] == '_id' or col in indexDict:
            create_defs.append('index(%s)' % col)
    cmd = 'create table if not exists %s (%s)' % (tableName,
                                                  ','.join(create_defs))
    cursor.execute(cmd) # CREATE THE TABLE IN THE DATABASE


def storeRow(cursor, tableName, row):
    row_format = ','.join(len(row) * ['%s'])
    cmd = 'insert into %s values (%s)' % (tableName, row_format)
    cursor.execute(cmd, tuple(row.values()))


def storeRowDelayed(cursor, tableName, row):
    row_format = ','.join(len(row) * ['%s'])
    cmd = 'insert delayed into %s values (%s)' % (tableName, row_format)
    cursor.execute(cmd, tuple(row.values()))


class TableGroup(dict):
    'provide attribute access to dbname qualified tablenames'

    def __init__(self, db='test', suffix=None, **kw):
        dict.__init__(self)
        self.db=db
        if suffix is not None:
            self.suffix=suffix
        for k, v in kw.items():
            if v is not None and '.' not in v:
                v=self.db+'.'+v  # ADD DATABASE NAME AS PREFIX
            self[k]=v

    def __getattr__(self, k):
        return self[k]


def sqlite_connect(*args, **kwargs):
    sqlite = import_sqlite()
    connection = sqlite.connect(*args, **kwargs)
    cursor = connection.cursor()
    return connection, cursor


class DBServerInfo(object):
    'picklable reference to a database server'

    def __init__(self, moduleName='MySQLdb', serverSideCursors=False,
                 blockIterators=True, *args, **kwargs):
        try:
            self.__class__ = _DBServerModuleDict[moduleName]
        except KeyError:
            raise ValueError('Module name not found in _DBServerModuleDict: '\
                             + moduleName)
        self.moduleName = moduleName
        self.args = args  # connection arguments
        self.kwargs = kwargs
        self.serverSideCursors = serverSideCursors
        self.custom_iter_keys = blockIterators
        if self.serverSideCursors and not self.custom_iter_keys:
            raise ValueError('serverSideCursors=True requires \
                             blockIterators=True!')

    def cursor(self):
        """returns cursor associated with the DB server info (reused)"""
        try:
            return self._cursor
        except AttributeError:
            self._start_connection()
            return self._cursor

    def new_cursor(self, arraysize=None):
        """returns a NEW cursor; you must close it yourself! """
        if not hasattr(self, '_connection'):
            self._start_connection()
        cursor = self._connection.cursor()
        if arraysize is not None:
            cursor.arraysize = arraysize
        return cursor

    def close(self):
        """Close file containing this database"""
        self._cursor.close()
        self._connection.close()
        del self._cursor
        del self._connection

    def __getstate__(self):
        """return all picklable arguments"""
        return dict(args=self.args, kwargs=self.kwargs,
                    moduleName=self.moduleName,
                    serverSideCursors=self.serverSideCursors,
                    custom_iter_keys=self.custom_iter_keys)


class MySQLServerInfo(DBServerInfo):
    'customized for MySQLdb SSCursor support via new_cursor()'
    _serverType = 'mysql'

    def _start_connection(self):
        self._connection, self._cursor = mysql_connect(*self.args,
                                                       **self.kwargs)

    def new_cursor(self, arraysize=None):
        'provide streaming cursor support'
        if not self.serverSideCursors: # use regular MySQLdb cursor
            return DBServerInfo.new_cursor(self, arraysize)
        try:
            conn = self._conn_sscursor
        except AttributeError:
            self._conn_sscursor, cursor = mysql_connect(useStreaming=True,
                                                        *self.args,
                                                        **self.kwargs)
        else:
            cursor = self._conn_sscursor.cursor()
        if arraysize is not None:
            cursor.arraysize = arraysize
        return cursor

    def close(self):
        DBServerInfo.close(self)
        try:
            self._conn_sscursor.close()
            del self._conn_sscursor
        except AttributeError:
            pass

    def iter_keys(self, db, cursor, map_f=iter,
                  cache_f=lambda x: [t[0] for t in x], **kwargs):
        block_iterator = BlockIterator(db, cursor, **kwargs)
        try:
            cache_f = block_iterator.cache_f
        except AttributeError:
            pass
        return db.generic_iterator(cursor=cursor, cache_f=cache_f,
                                   map_f=map_f, fetch_f=block_iterator)


class CursorCloser(object):
    """container for ensuring cursor.close() is called, when this obj deleted.
    For Python 2.5+, we could replace this with a try... finally clause
    in a generator function such as generic_iterator(); see PEP 342 or
    What's New in Python 2.5.  """

    def __init__(self, cursor):
        self.cursor = cursor

    def __del__(self):
        self.cursor.close()


class BlockIterator(CursorCloser):
    'workaround for MySQLdb iteration horrible performance'

    def __init__(self, db, cursor, selectCols, whereClause='', **kwargs):
        self.db = db
        self.cursor = cursor
        self.selectCols = selectCols
        self.kwargs = kwargs
        self.whereClause = ''
        if kwargs['orderBy']: # use iterSQL/iterColumns for WHERE / SELECT
            self.whereSQL = db.iterSQL
            if selectCols == '*': # extracting all columns
                self.whereParams = [db.data[col] for col in db.iterColumns]
            else: # selectCols is single column
                iterColumns = list(db.iterColumns)
                try: # if selectCols in db.iterColumns, just use that
                    i = iterColumns.index(selectCols)
                except ValueError: # have to append selectCols
                    i = len(db.iterColumns)
                    iterColumns += [selectCols]
                self.selectCols = ','.join(iterColumns)
                self.whereParams = range(len(db.iterColumns))
                if i > 0: # need to extract desired column
                    self.cache_f = lambda x: [t[i] for t in x]
        else: # just use primary key
            self.whereSQL = 'WHERE %s>%%s' % db.primary_key
            self.whereParams = (db.data[db.primary_key],)
        self.params = ()
        self.done = False

    def __call__(self):
        'get the next block of data'
        if self.done:
            return ()
        self.db._select(self.whereClause, self.params, cursor=self.cursor,
                        limit='LIMIT %s' % self.cursor.arraysize,
                        selectCols=self.selectCols, **(self.kwargs))
        rows = self.cursor.fetchall()
        if len(rows) < self.cursor.arraysize: # iteration complete
            self.done = True
            return rows
        lastrow = rows[-1] # extract params from the last row in this block
        if len(lastrow) > 1:
            self.params = [lastrow[icol] for icol in self.whereParams]
        else:
            self.params = lastrow
        self.whereClause = self.whereSQL
        return rows


class SQLiteServerInfo(DBServerInfo):
    """picklable reference to a sqlite database"""
    _serverType = 'sqlite'

    def __init__(self, database, *args, **kwargs):
        """Takes same arguments as sqlite3.connect()"""
        DBServerInfo.__init__(self, 'sqlite3',  # save abs path!
                              database=SourceFileName(database),
                              *args, **kwargs)

    def _start_connection(self):
        self._connection, self._cursor = sqlite_connect(*self.args,
                                                        **self.kwargs)

    def __getstate__(self):
        database = self.kwargs.get('database', False) or self.args[0]
        if database == ':memory:':
            raise ValueError('SQLite in-memory database is not picklable!')
        return DBServerInfo.__getstate__(self)

# list of DBServerInfo subclasses for different modules
_DBServerModuleDict = dict(MySQLdb=MySQLServerInfo,
                           sqlite3=SQLiteServerInfo)


class MapView(object, UserDict.DictMixin):
    'general purpose 1:1 mapping defined by any SQL query'

    def __init__(self, sourceDB, targetDB, viewSQL, cursor=None,
                 serverInfo=None, inverseSQL=None, **kwargs):
        self.sourceDB = sourceDB
        self.targetDB = targetDB
        self.viewSQL = viewSQL
        self.inverseSQL = inverseSQL
        if cursor is None:
            if serverInfo is not None: # get cursor from serverInfo
                cursor = serverInfo.cursor()
            else:
                try: # can we get it from our other db?
                    serverInfo = sourceDB.serverInfo
                except AttributeError:
                    raise ValueError('you must provide serverInfo or cursor!')
                else:
                    cursor = serverInfo.cursor()
        self.cursor = cursor
        self.serverInfo = serverInfo
        self.get_sql_format(False) # get sql formatter for this db interface

    _schemaModuleDict = _schemaModuleDict # default module list
    get_sql_format = get_table_schema

    def __getitem__(self, k):
        if not hasattr(k, 'db') or k.db is not self.sourceDB:
            raise KeyError('object is not in the sourceDB bound to this map!')
        sql, params = self._format_query(self.viewSQL, (k.id, ))
        self.cursor.execute(sql, params) # formatted for this db interface
        t = self.cursor.fetchmany(2) # get at most two rows
        if len(t) != 1:
            raise KeyError('%s not found in MapView, or not unique'
                           % str(k))
        return self.targetDB[t[0][0]] # get the corresponding object

    _pickleAttrs = dict(sourceDB=0, targetDB=0, viewSQL=0, serverInfo=0,
                        inverseSQL=0)
    __getstate__ = standard_getstate
    __setstate__ = standard_setstate
    __setitem__ = __delitem__ = clear = pop = popitem = update = \
                  setdefault = read_only_error

    def __iter__(self):
        'only yield sourceDB items that are actually in this mapping!'
        for k in self.sourceDB.itervalues():
            try:
                self[k]
                yield k
            except KeyError:
                pass

    def keys(self):
        return [k for k in self] # don't use list(self); causes infinite loop!

    def __invert__(self):
        try:
            return self._inverse
        except AttributeError:
            if self.inverseSQL is None:
                raise ValueError('this MapView has no inverseSQL!')
            self._inverse = self.__class__(self.targetDB, self.sourceDB,
                                           self.inverseSQL, self.cursor,
                                           serverInfo=self.serverInfo,
                                           inverseSQL=self.viewSQL)
            self._inverse._inverse = self
            return self._inverse


class GraphViewEdgeDict(UserDict.DictMixin):
    'edge dictionary for GraphView: just pre-loaded on init'

    def __init__(self, g, k):
        self.g = g
        self.k = k
        sql, params = self.g._format_query(self.g.viewSQL, (k.id, ))
        self.g.cursor.execute(sql, params) # run the query
        l = self.g.cursor.fetchall() # get results
        if len(l) <= 0:
            raise KeyError('key %s not in GraphView' % k.id)
        self.targets = [t[0] for t in l] # preserve order of the results
        d = {} # also keep targetID:edgeID mapping
        if self.g.edgeDB is not None: # save with edge info
            for t in l:
                d[t[0]] = t[1]
        else:
            for t in l:
                d[t[0]] = None
        self.targetDict = d

    def __len__(self):
        return len(self.targets)

    def __iter__(self):
        for k in self.targets:
            yield self.g.targetDB[k]

    def keys(self):
        return list(self)

    def iteritems(self):
        if self.g.edgeDB is not None: # save with edge info
            for k in self.targets:
                yield (self.g.targetDB[k], self.g.edgeDB[self.targetDict[k]])
        else: # just save the list of targets, no edge info
            for k in self.targets:
                yield (self.g.targetDB[k], None)

    def __getitem__(self, o, exitIfFound=False):
        'for the specified target object, return its associated edge object'
        try:
            if o.db is not self.g.targetDB:
                raise KeyError('key is not part of targetDB!')
            edgeID = self.targetDict[o.id]
        except AttributeError:
            raise KeyError('key has no id or db attribute?!')
        if exitIfFound:
            return
        if self.g.edgeDB is not None: # return the edge object
            return self.g.edgeDB[edgeID]
        else: # no edge info
            return None

    def __contains__(self, o):
        try:
            self.__getitem__(o, True) # raise KeyError if not found
            return True
        except KeyError:
            return False

    __setitem__ = __delitem__ = clear = pop = popitem = update = \
                  setdefault = read_only_error


class GraphView(MapView):
    'general purpose graph interface defined by any SQL query'

    def __init__(self, sourceDB, targetDB, viewSQL, cursor=None, edgeDB=None,
                 **kwargs):
        '''if edgeDB not None, viewSQL query must return
        (targetID, edgeID) tuples'''
        self.edgeDB = edgeDB
        MapView.__init__(self, sourceDB, targetDB, viewSQL, cursor, **kwargs)

    def __getitem__(self, k):
        if not hasattr(k, 'db') or k.db is not self.sourceDB:
            raise KeyError('object is not in the sourceDB bound to this map!')
        return GraphViewEdgeDict(self, k)
    _pickleAttrs = MapView._pickleAttrs.copy()
    _pickleAttrs.update(dict(edgeDB=0))


class SQLSequence(SQLRow, SequenceBase):
    """Transparent access to a DB row representing a sequence.
    Does not cache the sequence string in memory -- uses SQL queries to
    retrieve just the desired slice as needed.
    By default expects a column named 'length' to provide sequence length;
    use attrAlias to remap to an SQL expression if needed.
    """

    def _init_subclass(cls, db, **kwargs):
        db.seqInfoDict = db # db will act as its own seqInfoDict
        SQLRow._init_subclass(db=db, **kwargs)
    _init_subclass = classmethod(_init_subclass)

    def __init__(self, id):
        SQLRow.__init__(self, id)
        SequenceBase.__init__(self)

    def __len__(self):
        return self.length

    def strslice(self, start, end):
        "Efficient access to slice of a sequence, useful for huge contigs"
        return self._select('%%(SUBSTRING)s(%s %%(SUBSTR_FROM)s %d \
                            %%(SUBSTR_FOR)s %d)' % (self.db._attrSQL('seq'),
                                                    start + 1, end - start))


class DNASQLSequence(SQLSequence):
    _seqtype=DNA_SEQTYPE


class RNASQLSequence(SQLSequence):
    _seqtype=RNA_SEQTYPE


class ProteinSQLSequence(SQLSequence):
    _seqtype=PROTEIN_SEQTYPE

class SQLSequenceCached(TupleO, SequenceBase):
    '''Caches complete sequence string when initially constructed.
    By default expects it as column "seq"; use attrAlias to remap to another
    column if needed.'''
    def _init_subclass(cls, db, **kwargs):
        db.seqInfoDict = db # db will act as its own seqInfoDict
        TupleO._init_subclass(db=db, **kwargs)
    _init_subclass = classmethod(_init_subclass)

    def __init__(self, data):
        TupleO.__init__(self, data)
        SequenceBase.__init__(self)

class DNASQLSequenceCached(SQLSequenceCached):
    _seqtype=DNA_SEQTYPE


class RNASQLSequenceCached(SQLSequenceCached):
    _seqtype=RNA_SEQTYPE


class ProteinSQLSequenceCached(SQLSequenceCached):
    _seqtype=PROTEIN_SEQTYPE


########NEW FILE########
__FILENAME__ = translationDB
from seqdb import SequenceDB, BasicSeqInfoDict
from annotation import AnnotationDB, TranslationAnnot, TranslationAnnotSlice
import classutil
import sequence
import UserDict


class SeqTranslator(sequence.SequenceBase):
    """Translator object for positive or minus strand of a sequence.
    Slicing returns TranslationAnnotSlice of the appropriate
    TranslationAnnot representing one of the six possible frames for
    this sequence."""

    def __init__(self, db, id, reversePath=None):
        self.id = id
        sequence.SequenceBase.__init__(self)
        if reversePath: # create top-level object for reverse strand
            self.orientation = -1
            self.start = -len(self)
            self.stop = 0
            self._reverse = reversePath
        if self.id not in self.db.seqDB:
            raise KeyError('sequence %s not in db %s' % (self.id, self.db))

    def __getitem__(self, k):
        """get TranslationAnnotSlice for coordinates given by slice k """
        start = k.start                 # deal with [:stop] slices
        if start is None:
            start = self.start
        stop = k.stop                   # deal with [start:] slices
        if stop is None:
            stop = self.stop

        annoID = self._get_anno_id(start)
        a = self.db.annodb[annoID] # get TranslationAnnot object
        s = a.sequence # corresponding nucleotide region

        return a[(start - s.start) / 3: (stop - s.start) / 3]

    def absolute_slice(self, start, stop):
        """get protein slice in absolute nucleotide coords;
        perform negation before slicing """
        if start<0:
            return (-self)[start:stop]
        else:
            return self[start:stop]

    def __len__(self):
        return self.db.seqInfoDict[self.id].length

    def __neg__(self):
        """get SeqTranslator for the opposite strand """
        try:
            return self._reverse
        except AttributeError:
            self._reverse = self.__class__(self.db, self.id,
                                           reversePath=self)
            return self._reverse

    def _get_anno_id(self, start):
        """get annotation ID for frame starting at start """
        if self.orientation > 0: # positive strand
            return '%s:%d' % (self.id, start % 3)
        else: # negative strand
            return '%s:-%d' % (self.id, (-start) % 3)

    def iter_frames(self):
        'iterate over the 6 possible frames, yielding TranslationAnnot'
        for frame in ('0', '1', '2', '-0', '-1', '-2'):
            yield self.db.annodb['%s:%s' % (self.id, frame)]

    def __repr__(self):
        return 'SeqTranslator(' + sequence.SequenceBase.__repr__(self) + ')'


class TranslationDB(SequenceDB):
    """Provides an automatic translation interface for a nucleotide sequence
    database: slicing of top-level sequence objects will return the
    corresponding TranslationAnnotSlice for that slice, i.e. the
    translated protein sequence, rather than the nucleotide sequence. """
    itemClass = SeqTranslator
    _seqtype = sequence.DNA_SEQTYPE

    def __init__(self, seqDB, **kwargs):
        self.seqDB = seqDB
        try:
            self.seqInfoDict = seqDB.seqInfoDict
        except AttributeError:
            self.seqInfoDict = BasicSeqInfoDict(seqDB)
        self.annodb = AnnotationDB(SixFrameInfo(seqDB), seqDB,
                                   itemClass=TranslationAnnot,
                                   itemSliceClass=TranslationAnnotSlice,
                                   sliceAttrDict=dict(id=0, start=1, stop=2),
                                   checkFirstID=False)
        SequenceDB.__init__(self, **kwargs)


class SixFrameInfo(object, UserDict.DictMixin):
    """Dictionary of slice info for all six frames of each seq in seqDB. """

    def __init__(self, seqDB):
        self.seqDB = seqDB

    def __getitem__(self, k):
        "convert ID of form seqID:frame into slice info tuple"
        i = k.rfind(':')
        if i < 0:
            raise KeyError('invalid TranslationInfo key: %s' % (k, ))
        seqID = k[:i]
        length = len(self.seqDB[seqID]) # sequence length
        frame = int(k[i+1:])
        if k[i+1] == '-': # negative frame -0, -1, or -2
            return (seqID, -(length - ((length + frame) % 3)), frame)
        else: # positive frame 0, 1 or 2
            return (seqID, frame, length - ((length - frame) % 3))

    def __len__(self):
        return 6 * len(self.seqDB)

    def __iter__(self):
        for seqID in self.seqDB:
            for frame in (':0', ':1', ':2', ':-0', ':-1', ':-2'):
                yield seqID + frame

    def keys(self):
        return list(self)

    # these methods should not be implemented for read-only database.
    clear = setdefault = pop = popitem = copy = update = \
            classutil.read_only_error


def get_translation_db(seqDB):
    """Use cached seqDB.translationDB if already present, or create it """
    try:
        return seqDB.translationDB
    except AttributeError: # create a new TranslationAnnot DB
        tdb = TranslationDB(seqDB)
        try:
            seqDB.translationDB = tdb
        except AttributeError:
            pass # won't let us cache? Just hand back the TranslationDB
        return tdb

########NEW FILE########
__FILENAME__ = xnestedlist
import cnestedlist
from nlmsa_utils import EmptySliceError, EmptySlice
import sequence


class NLMSAServer(cnestedlist.NLMSA):
    'serves NLMSA via serializable method calls for XMLRPC'
    xmlrpc_methods = {'getSlice': 0, 'getInfo': 0}

    def getSlice(self, seqID, start, stop):
        'perform an interval query and return results as raw ivals'
        try:
            seq = self.seqDict[seqID]
            nlmsa_id, ns, offset = self.seqs[seq] # GET UNION INFO FOR THIS SEQ
        except KeyError:
            return '' # failure code
        ival = sequence.absoluteSlice(seq, start, stop) # GET THE INTERVAL
        try:
            myslice = self[ival] # DO THE QUERY
        except EmptySliceError:
            return 'EMPTY'
        except KeyError:
            return ''  # FAILURE CODE
        ivals = myslice.rawIvals() # GET RAW INTERVAL DATA
        d = {}
        # Save index info for source seq.
        d[nlmsa_id] = self.seqs.IDdict[str(nlmsa_id)]
        for v in ivals: # SAVE INDEX INFO FOR TARGET SEQS
            id = v[2] # target_id NLMSA_ID
            if not self.seqlist.is_lpo(id):
                # Only non-LPO seqs stored in this index.
                d[id] = self.seqs.IDdict[str(id)]
        # XMLRPC can't handle int dictionaries, use a list.
        l = [(key, val) for key, val in d.items()]
        # List of aligned ivals, list of (nlmsa_id, (seqID, nsID)).
        return nlmsa_id, ivals, l

    def getInfo(self):
        'return list of tuples describing NLMSASequences in this NLMSA'
        l = []
        for ns in self.seqlist:
            l.append((ns.id, ns.is_lpo, ns.length, ns.is_union))
        return l


class NLMSAClient(cnestedlist.NLMSA):
    'client for accessing NLMSAServer via XMLRPC'

    def __init__(self, url=None, name=None, idDictClass=dict, **kwargs):
        cnestedlist.NLMSA.__init__(self, mode='xmlrpc',
                                   idDictClass=idDictClass, **kwargs)
        import coordinator
        self.server = coordinator.get_connection(url, name)
        self.url = url
        self.name = name
        l = self.server.getInfo() # READ NS INFO TABLE
        for nsID, is_lpo, nsLength, is_union in l:
            # is_lpo is automatic below.
            ns = cnestedlist.NLMSASequence(self, None, None, 'onDemand',
                                           is_union, nsLength)
            self.addToSeqlist(ns) # ADD THIS TO THE INDEX

    def close(self):
        pass # required interface, but nothing to do

    def doSlice(self, seq):
        '''getSlice from the server, and create an NLMSASlice object
        from results'''
        result = self.server.getSlice(self.seqs.getSeqID(seq), seq.start,
                                      seq.stop)
        if result == '':
            raise KeyError('this interval is not aligned!')
        elif result == 'EMPTY':
            raise EmptySliceError
        id, l, d = result
        for nlmsaID, (seqID, nsID) in d: # SAVE SEQ INFO TO INDEX
            self.seqs.saveSeq(seqID, nsID, 0, nlmsaID)
        return id, l # HAND BACK THE RAW INTEGER INTERVAL DATA

    def __getitem__(self, k):
        'directly call slice without any ID lookup -- will be done server-side'
        try:
            return cnestedlist.NLMSASlice(self.seqlist[0], k.start, k.stop,
                                          -1, -1, k)
        except EmptySliceError:
            return EmptySlice(k)

    def __getstate__(self):
        return dict(url=self.url, name=self.name, seqDict=self.seqDict)

########NEW FILE########
__FILENAME__ = annotation_dm2_megatest
import unittest
from testlib import testutil, PygrTestProgram

import ConfigParser
import os
import string
import sys

from pygr.mapping import Collection
import pygr.Data

try:
    import hashlib
except ImportError:
    import md5 as hashlib

config = ConfigParser.ConfigParser({'testOutputBaseDir': '.',
                                    'smallSampleKey': ''})
config.read([os.path.join(os.path.expanduser('~'), '.pygrrc'),
             os.path.join(os.path.expanduser('~'), 'pygr.cfg'),
             '.pygrrc', 'pygr.cfg'])
msaDir = config.get('megatests_dm2', 'msaDir')
seqDir = config.get('megatests_dm2', 'seqDir')
smallSampleKey = config.get('megatests_dm2', 'smallSampleKey')
testInputDB = config.get('megatests', 'testInputDB')
testInputDir = config.get('megatests', 'testInputDir')
testOutputBaseDir = config.get('megatests', 'testOutputBaseDir')

if smallSampleKey:
    smallSamplePostfix = '_' + smallSampleKey
else:
    smallSamplePostfix = ''

## msaDir CONTAINS PRE-BUILT NLMSA
## seqDir CONTAINS GENOME ASSEMBLIES AND THEIR SEQDB FILES
## TEST INPUT/OUPTUT FOR COMPARISON, THESE FILES SHOULD BE IN THIS DIRECTORY
##        exonAnnotFileName = 'Annotation_ConservedElement_Exons_dm2.txt'
##        intronAnnotFileName = 'Annotation_ConservedElement_Introns_dm2.txt'
##        stopAnnotFileName = 'Annotation_ConservedElement_Stop_dm2.txt'
## testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList)) SHOULD
## BE DELETED IF YOU WANT TO RUN IN '.'

# DIRECTIONARY FOR DOC STRING OF SEQDB
docStringDict = {
    'anoGam1': 'A. gambiae Genome (February 2003)',
    'apiMel2': 'A. mellifera Genome (January 2005)',
    'dm2': 'D. melanogaster Genome (April 2004)',
    'dp4': 'D. pseudoobscura Genome (February 2006)',
    'droAna3': 'D. ananassae Genome (February 2006)',
    'droEre2': 'D. erecta Genome (February 2006)',
    'droGri2': 'D. grimshawi Genome (February 2006)',
    'droMoj3': 'D. mojavensis Genome (February 2006)',
    'droPer1': 'D. persimilis Genome (October 2005)',
    'droSec1': 'D. sechellia Genome (October 2005)',
    'droSim1': 'D. simulans Genome (April 2005)',
    'droVir3': 'D. virilis Genome (February 2006)',
    'droWil1': 'D. willistoni Genome (February 2006)',
    'droYak2': 'D. yakuba Genome (November 2005)',
    'triCas2': 'T. castaneum Genome (September 2005)',
    }

# GENOME ASSEMBLY LIST FOR DM2 MULTIZ15WAY
msaSpeciesList = ['anoGam1', 'apiMel2', 'dm2', 'dp4', 'droAna3', 'droEre2',
                  'droGri2', 'droMoj3', 'droPer1', 'droSec1', 'droSim1',
                  'droVir3', 'droWil1', 'droYak2', 'triCas2']


class PygrBuildNLMSAMegabase(unittest.TestCase):

    def setUp(self, testDir=None):
        '''restrict megatest to an initially empty directory, need
        large space to perform'''
        import random
        tmpList = [c for c in 'PygrBuildNLMSAMegabase']
        random.shuffle(tmpList)
        # Comment out the next line to run in current directory.
        testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList))
        if testDir is None:
            testDir = 'TEST_' + ''.join(tmpList)
        try:
            os.mkdir(testDir)
            testDir = os.path.realpath(testDir)
        except:
            raise IOError
        self.path = testDir
        try:
            tmpFileName = os.path.join(testDir, 'DELETE_THIS_TEMP_FILE')
            open(tmpFileName, 'w').write('A' * 1024 * 1024)
        except:
            raise IOError
        pygr.Data.update(self.path)
        from pygr import seqdb
        for orgstr in msaSpeciesList:
            genome = seqdb.BlastDB(os.path.join(seqDir, orgstr))
            genome.__doc__ = docStringDict[orgstr]
            pygr.Data.addResource('TEST.Seq.Genome.' + orgstr, genome)
        pygr.Data.save()

    def copyFile(self, filename): # COPY A FILE INTO TEST DIRECTORY
        newname = os.path.join(self.path, os.path.basename(filename))
        open(newname, 'w').write(open(filename, 'r').read())
        return newname

    def tearDown(self):
        'delete the temporary directory and files, restore pygr.Data path'
        # Delete them bottom-up for obvious reasons.
        for dirpath, subdirs, files in os.walk(self.path, topdown=False):
            # Note: this part may not work in directories on NFS due to
            # creation of lock files (.nfsXXXXXXXXX), which will only allow
            # deletion after pygr.Data has been closed.
            for filename in files:
                os.remove(os.path.join(dirpath, filename))
            os.rmdir(dirpath)
        # Restore original pygr.Data path to remedy lack of isolation
        # between tests from the same run
        pygr.Data.update(None)


class Build_Test(PygrBuildNLMSAMegabase):

    def test_seqdb(self):
        'Check pygr.Data contents'
        l = pygr.Data.dir('TEST')
        preList = ['TEST.Seq.Genome.' + orgstr for orgstr in msaSpeciesList]
        assert l == preList

    def test_collectionannot(self):
        'Test building an AnnotationDB from file'
        from pygr import seqdb, cnestedlist, sqlgraph
        dm2 = pygr.Data.getResource('TEST.Seq.Genome.dm2')
        # BUILD ANNOTATION DATABASE FOR REFSEQ EXONS
        exon_slices = Collection(
            filename=os.path.join(self.path, 'refGene_exonAnnot_dm2.cdb'),
            intKeys=True, mode='cr', writeback=False)
        exon_db = seqdb.AnnotationDB(exon_slices, dm2,
                                     sliceAttrDict=dict(id=0, exon_id=1,
                                                        orientation=2,
                                                        gene_id=3, start=4,
                                                        stop=5))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_exonAnnot_dm2'), 'w',
                                pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir,
                                       'refGene_exonAnnot%s_dm2.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            exon_slices[row[1]] = row
            exon = exon_db[row[1]] # GET THE ANNOTATION OBJECT FOR THIS EXON
            msa.addAnnotation(exon) # SAVE IT TO GENOME MAPPING
        exon_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        exon_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        exon_db.__doc__ = 'Exon Annotation Database for dm2'
        pygr.Data.addResource('TEST.Annotation.dm2.exons', exon_db)
        msa.__doc__ = 'NLMSA Exon for dm2'
        pygr.Data.addResource('TEST.Annotation.NLMSA.dm2.exons', msa)
        exon_schema = pygr.Data.ManyToManyRelation(dm2, exon_db,
                                                   bindAttrs=('exon1', ))
        exon_schema.__doc__ = 'Exon Schema for dm2'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.dm2.exons', exon_schema)
        # BUILD ANNOTATION DATABASE FOR REFSEQ SPLICES
        splice_slices = Collection(
            filename=os.path.join(self.path, 'refGene_spliceAnnot_dm2.cdb'),
            intKeys=True, mode='cr', writeback=False)
        splice_db = seqdb.AnnotationDB(splice_slices, dm2,
                                       sliceAttrDict=dict(id=0, splice_id=1,
                                                          orientation=2,
                                                          gene_id=3, start=4,
                                                          stop=5))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_spliceAnnot_dm2'), 'w',
                                pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir,
                                       'refGene_spliceAnnot%s_dm2.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            splice_slices[row[1]] = row
            # GET THE ANNOTATION OBJECT FOR THIS EXON
            splice = splice_db[row[1]]
            msa.addAnnotation(splice) # SAVE IT TO GENOME MAPPING
        splice_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        splice_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        splice_db.__doc__ = 'Splice Annotation Database for dm2'
        pygr.Data.addResource('TEST.Annotation.dm2.splices', splice_db)
        msa.__doc__ = 'NLMSA Splice for dm2'
        pygr.Data.addResource('TEST.Annotation.NLMSA.dm2.splices', msa)
        splice_schema = pygr.Data.ManyToManyRelation(dm2, splice_db,
                                                     bindAttrs=('splice1', ))
        splice_schema.__doc__ = 'Splice Schema for dm2'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.dm2.splices', splice_schema)
        # BUILD ANNOTATION DATABASE FOR MOST CONSERVED ELEMENTS FROM UCSC
        ucsc_slices = Collection(
            filename=os.path.join(self.path, 'phastConsElements15way_dm2.cdb'),
            intKeys=True, mode='cr', writeback=False)
        ucsc_db = seqdb.AnnotationDB(ucsc_slices, dm2,
                                     sliceAttrDict=dict(id=0, ucsc_id=1,
                                                        orientation=2,
                                                        gene_id=3, start=4,
                                                        stop=5))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'phastConsElements15way_dm2'),
                                'w', pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir,
                                       'phastConsElements15way%s_dm2.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            ucsc_slices[row[1]] = row
            ucsc = ucsc_db[row[1]] # GET THE ANNOTATION OBJECT FOR THIS EXON
            msa.addAnnotation(ucsc) # SAVE IT TO GENOME MAPPING
        ucsc_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        ucsc_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        ucsc_db.__doc__ = 'Most Conserved Elements for dm2'
        pygr.Data.addResource('TEST.Annotation.UCSC.dm2.mostconserved',
                              ucsc_db)
        msa.__doc__ = 'NLMSA for Most Conserved Elements for dm2'
        pygr.Data.addResource('TEST.Annotation.UCSC.NLMSA.dm2.mostconserved',
                              msa)
        ucsc_schema = pygr.Data.ManyToManyRelation(dm2, ucsc_db,
                                                   bindAttrs=('element1', ))
        ucsc_schema.__doc__ = 'Schema for UCSC Most Conserved Elements for dm2'
        pygr.Data.addSchema('TEST.Annotation.UCSC.NLMSA.dm2.mostconserved',
                            ucsc_schema)
        pygr.Data.save()
        pygr.Data.clear_cache() # force resources to reload when requested

        # QUERY TO EXON AND SPLICES ANNOTATION DATABASE
        dm2 = pygr.Data.getResource('TEST.Seq.Genome.dm2')
        exonmsa = pygr.Data.getResource('TEST.Annotation.NLMSA.dm2.exons')
        splicemsa = pygr.Data.getResource('TEST.Annotation.NLMSA.dm2.splices')
        conservedmsa = \
          pygr.Data.getResource('TEST.Annotation.UCSC.NLMSA.dm2.mostconserved')
        exons = pygr.Data.getResource('TEST.Annotation.dm2.exons')
        splices = pygr.Data.getResource('TEST.Annotation.dm2.splices')
        mostconserved = \
                pygr.Data.getResource('TEST.Annotation.UCSC.dm2.mostconserved')

        # OPEN DM2_MULTIZ15WAY NLMSA
        msa = cnestedlist.NLMSA(os.path.join(msaDir, 'dm2_multiz15way'), 'r',
                                trypath=[seqDir])

        exonAnnotFileName = os.path.join(testInputDir,
                                  'Annotation_ConservedElement_Exons%s_dm2.txt'
                                         % smallSamplePostfix)
        intronAnnotFileName = os.path.join(testInputDir,
                                'Annotation_ConservedElement_Introns%s_dm2.txt'
                                           % smallSamplePostfix)
        newexonAnnotFileName = os.path.join(self.path, 'new_Exons_dm2.txt')
        newintronAnnotFileName = os.path.join(self.path, 'new_Introns_dm2.txt')
        tmpexonAnnotFileName = self.copyFile(exonAnnotFileName)
        tmpintronAnnotFileName = self.copyFile(intronAnnotFileName)

        if smallSampleKey:
            chrList = [smallSampleKey]
        else:
            chrList = dm2.seqLenDict.keys()
            chrList.sort()

        outfile = open(newexonAnnotFileName, 'w')
        for chrid in chrList:
            slice = dm2[chrid]
            try:
                ex1 = exonmsa[slice]
            except KeyError:
                continue
            else:
                exlist1 = [(ix.exon_id, ix) for ix in ex1.keys()]
                exlist1.sort()
                for ixx, exon in exlist1:
                    saveList = []
                    tmp = exon.sequence
                    tmpexon = exons[exon.exon_id]
                    tmpslice = tmpexon.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'EXON', chrid, tmpexon.exon_id, tmpexon.gene_id, \
                            tmpslice.start, tmpslice.stop
                    try:
                        out1 = conservedmsa[tmp]
                    except KeyError:
                        pass
                    else:
                        elementlist = [(ix.ucsc_id, ix) for ix in out1.keys()]
                        elementlist.sort()
                        for iyy, element in elementlist:
                            if element.stop - element.start < 100:
                                continue
                            score = int(string.split(element.gene_id, '=')[1])
                            if score < 100:
                                continue
                            tmp2 = element.sequence
                            tmpelement = mostconserved[element.ucsc_id]
                            # FOR REAL ELEMENT COORDINATE
                            tmpslice2 = tmpelement.sequence
                            wlist2 = wlist1 + (tmpelement.ucsc_id,
                                               tmpelement.gene_id,
                                               tmpslice2.start, tmpslice2.stop)
                            slicestart, sliceend = max(tmp.start, tmp2.start),\
                                    min(tmp.stop, tmp2.stop)
                            tmp1 = msa.seqDict['dm2.' + chrid][slicestart:
                                                               sliceend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start < 100:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                if palign < 0.8 or pident < 0.8:
                                    continue
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpexonAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newexonAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

        outfile = open(newintronAnnotFileName, 'w')
        for chrid in chrList:
            slice = dm2[chrid]
            try:
                sp1 = splicemsa[slice]
            except:
                continue
            else:
                splist1 = [(ix.splice_id, ix) for ix in sp1.keys()]
                splist1.sort()
                for ixx, splice in splist1:
                    saveList = []
                    tmp = splice.sequence
                    tmpsplice = splices[splice.splice_id]
                    tmpslice = tmpsplice.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'INTRON', chrid, tmpsplice.splice_id, \
                            tmpsplice.gene_id, tmpslice.start, tmpslice.stop
                    try:
                        out1 = conservedmsa[tmp]
                    except KeyError:
                        pass
                    else:
                        elementlist = [(ix.ucsc_id, ix) for ix in out1.keys()]
                        elementlist.sort()
                        for iyy, element in elementlist:
                            if element.stop - element.start < 100:
                                continue
                            score = int(string.split(element.gene_id, '=')[1])
                            if score < 100:
                                continue
                            tmp2 = element.sequence
                            tmpelement = mostconserved[element.ucsc_id]
                            # FOR REAL ELEMENT COORDINATE
                            tmpslice2 = tmpelement.sequence
                            wlist2 = wlist1 + (tmpelement.ucsc_id,
                                               tmpelement.gene_id,
                                               tmpslice2.start, tmpslice2.stop)
                            slicestart, sliceend = max(tmp.start, tmp2.start),\
                                    min(tmp.stop, tmp2.stop)
                            tmp1 = msa.seqDict['dm2.' + chrid][slicestart:
                                                               sliceend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start < 100:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                if palign < 0.8 or pident < 0.8:
                                    continue
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpintronAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newintronAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

    def test_mysqlannot(self):
        'Test building an AnnotationDB from MySQL'
        from pygr import seqdb, cnestedlist, sqlgraph
        dm2 = pygr.Data.getResource('TEST.Seq.Genome.dm2')
        # BUILD ANNOTATION DATABASE FOR REFSEQ EXONS: MYSQL VERSION
        exon_slices = sqlgraph.SQLTableClustered(
            '%s.pygr_refGene_exonAnnot%s_dm2' % (testInputDB,
                                                 smallSamplePostfix),
            clusterKey='chromosome', maxCache=0)
        exon_db = seqdb.AnnotationDB(exon_slices, dm2,
                                     sliceAttrDict=dict(id='chromosome',
                                                        gene_id='name',
                                                        exon_id='exon_id'))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_exonAnnot_SQL_dm2'), 'w',
                                pairwiseMode=True, bidirectional=False)
        for id in exon_db:
            msa.addAnnotation(exon_db[id])
        exon_db.clear_cache() # not really necessary; cache should autoGC
        exon_slices.clear_cache()
        msa.build()
        exon_db.__doc__ = 'SQL Exon Annotation Database for dm2'
        pygr.Data.addResource('TEST.Annotation.SQL.dm2.exons', exon_db)
        msa.__doc__ = 'SQL NLMSA Exon for dm2'
        pygr.Data.addResource('TEST.Annotation.NLMSA.SQL.dm2.exons', msa)
        exon_schema = pygr.Data.ManyToManyRelation(dm2, exon_db,
                                                   bindAttrs=('exon2', ))
        exon_schema.__doc__ = 'SQL Exon Schema for dm2'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.SQL.dm2.exons', exon_schema)
        # BUILD ANNOTATION DATABASE FOR REFSEQ SPLICES: MYSQL VERSION
        splice_slices = sqlgraph.SQLTableClustered(
            '%s.pygr_refGene_spliceAnnot%s_dm2' % (testInputDB,
                                                   smallSamplePostfix),
            clusterKey='chromosome', maxCache=0)
        splice_db = seqdb.AnnotationDB(splice_slices, dm2,
                                       sliceAttrDict=dict(id='chromosome',
                                                          gene_id='name',
                                                        splice_id='splice_id'))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_spliceAnnot_SQL_dm2'),
                                'w', pairwiseMode=True, bidirectional=False)
        for id in splice_db:
            msa.addAnnotation(splice_db[id])
        splice_db.clear_cache() # not really necessary; cache should autoGC
        splice_slices.clear_cache()
        msa.build()
        splice_db.__doc__ = 'SQL Splice Annotation Database for dm2'
        pygr.Data.addResource('TEST.Annotation.SQL.dm2.splices', splice_db)
        msa.__doc__ = 'SQL NLMSA Splice for dm2'
        pygr.Data.addResource('TEST.Annotation.NLMSA.SQL.dm2.splices', msa)
        splice_schema = pygr.Data.ManyToManyRelation(dm2, splice_db,
                                                     bindAttrs=('splice2', ))
        splice_schema.__doc__ = 'SQL Splice Schema for dm2'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.SQL.dm2.splices',
                            splice_schema)
        # BUILD ANNOTATION DATABASE FOR MOST CONSERVED ELEMENTS FROM UCSC:
        # MYSQL VERSION
        ucsc_slices = sqlgraph.SQLTableClustered(
            '%s.pygr_phastConsElements15way%s_dm2' % (testInputDB,
                                                      smallSamplePostfix),
            clusterKey='chromosome', maxCache=0)
        ucsc_db = seqdb.AnnotationDB(ucsc_slices, dm2,
                                     sliceAttrDict=dict(id='chromosome',
                                                        gene_id='name',
                                                        ucsc_id='ucsc_id'))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'phastConsElements15way_SQL_dm2'),
                                'w', pairwiseMode=True, bidirectional=False)
        for id in ucsc_db:
            msa.addAnnotation(ucsc_db[id])
        ucsc_db.clear_cache() # not really necessary; cache should autoGC
        ucsc_slices.clear_cache()
        msa.build()
        ucsc_db.__doc__ = 'SQL Most Conserved Elements for dm2'
        pygr.Data.addResource('TEST.Annotation.UCSC.SQL.dm2.mostconserved',
                              ucsc_db)
        msa.__doc__ = 'SQL NLMSA for Most Conserved Elements for dm2'
        pygr.Data.addResource(
            'TEST.Annotation.UCSC.NLMSA.SQL.dm2.mostconserved', msa)
        ucsc_schema = pygr.Data.ManyToManyRelation(dm2, ucsc_db,
                                                   bindAttrs=('element2', ))
        ucsc_schema.__doc__ = \
                'SQL Schema for UCSC Most Conserved Elements for dm2'
        pygr.Data.addSchema('TEST.Annotation.UCSC.NLMSA.SQL.dm2.mostconserved',
                            ucsc_schema)
        pygr.Data.save()
        pygr.Data.clear_cache()

        # QUERY TO EXON AND SPLICES ANNOTATION DATABASE
        dm2 = pygr.Data.getResource('TEST.Seq.Genome.dm2')
        exonmsa = pygr.Data.getResource('TEST.Annotation.NLMSA.SQL.dm2.exons')
        splicemsa = \
                pygr.Data.getResource('TEST.Annotation.NLMSA.SQL.dm2.splices')
        conservedmsa = \
      pygr.Data.getResource('TEST.Annotation.UCSC.NLMSA.SQL.dm2.mostconserved')
        exons = pygr.Data.getResource('TEST.Annotation.SQL.dm2.exons')
        splices = pygr.Data.getResource('TEST.Annotation.SQL.dm2.splices')
        mostconserved = \
            pygr.Data.getResource('TEST.Annotation.UCSC.SQL.dm2.mostconserved')

        # OPEN DM2_MULTIZ15WAY NLMSA
        msa = cnestedlist.NLMSA(os.path.join(msaDir, 'dm2_multiz15way'), 'r',
                                trypath=[seqDir])

        exonAnnotFileName = os.path.join(testInputDir,
                                  'Annotation_ConservedElement_Exons%s_dm2.txt'
                                         % smallSamplePostfix)
        intronAnnotFileName = os.path.join(testInputDir,
                                'Annotation_ConservedElement_Introns%s_dm2.txt'
                                           % smallSamplePostfix)
        newexonAnnotFileName = os.path.join(self.path, 'new_Exons_dm2.txt')
        newintronAnnotFileName = os.path.join(self.path, 'new_Introns_dm2.txt')
        tmpexonAnnotFileName = self.copyFile(exonAnnotFileName)
        tmpintronAnnotFileName = self.copyFile(intronAnnotFileName)

        if smallSampleKey:
            chrList = [smallSampleKey]
        else:
            chrList = dm2.seqLenDict.keys()
            chrList.sort()

        outfile = open(newexonAnnotFileName, 'w')
        for chrid in chrList:
            slice = dm2[chrid]
            try:
                ex1 = exonmsa[slice]
            except KeyError:
                continue
            else:
                exlist1 = [(ix.exon_id, ix) for ix in ex1.keys()]
                exlist1.sort()
                for ixx, exon in exlist1:
                    saveList = []
                    tmp = exon.sequence
                    tmpexon = exons[exon.exon_id]
                    tmpslice = tmpexon.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'EXON', chrid, tmpexon.exon_id, tmpexon.gene_id, \
                            tmpslice.start, tmpslice.stop
                    try:
                        out1 = conservedmsa[tmp]
                    except KeyError:
                        pass
                    else:
                        elementlist = [(ix.ucsc_id, ix) for ix in out1.keys()]
                        elementlist.sort()
                        for iyy, element in elementlist:
                            if element.stop - element.start < 100:
                                continue
                            score = int(string.split(element.gene_id, '=')[1])
                            if score < 100:
                                continue
                            tmp2 = element.sequence
                            tmpelement = mostconserved[element.ucsc_id]
                            # FOR REAL ELEMENT COORDINATE
                            tmpslice2 = tmpelement.sequence
                            wlist2 = wlist1 + (tmpelement.ucsc_id,
                                               tmpelement.gene_id,
                                               tmpslice2.start, tmpslice2.stop)
                            slicestart, sliceend = max(tmp.start, tmp2.start),\
                                    min(tmp.stop, tmp2.stop)
                            tmp1 = msa.seqDict['dm2.' + chrid][slicestart:
                                                               sliceend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start < 100:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                if palign < 0.8 or pident < 0.8:
                                    continue
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpexonAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newexonAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

        outfile = open(newintronAnnotFileName, 'w')
        for chrid in chrList:
            slice = dm2[chrid]
            try:
                sp1 = splicemsa[slice]
            except:
                continue
            else:
                splist1 = [(ix.splice_id, ix) for ix in sp1.keys()]
                splist1.sort()
                for ixx, splice in splist1:
                    saveList = []
                    tmp = splice.sequence
                    tmpsplice = splices[splice.splice_id]
                    tmpslice = tmpsplice.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'INTRON', chrid, tmpsplice.splice_id, \
                            tmpsplice.gene_id, tmpslice.start, tmpslice.stop
                    try:
                        out1 = conservedmsa[tmp]
                    except KeyError:
                        pass
                    else:
                        elementlist = [(ix.ucsc_id, ix) for ix in out1.keys()]
                        elementlist.sort()
                        for iyy, element in elementlist:
                            if element.stop - element.start < 100:
                                continue
                            score = int(string.split(element.gene_id, '=')[1])
                            if score < 100:
                                continue
                            tmp2 = element.sequence
                            tmpelement = mostconserved[element.ucsc_id]
                            # FOR REAL ELEMENT COORDINATE
                            tmpslice2 = tmpelement.sequence
                            wlist2 = wlist1 + (tmpelement.ucsc_id,
                                               tmpelement.gene_id,
                                               tmpslice2.start, tmpslice2.stop)
                            slicestart, sliceend = max(tmp.start, tmp2.start),\
                                    min(tmp.stop, tmp2.stop)
                            tmp1 = msa.seqDict['dm2.' + chrid][slicestart:
                                                               sliceend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start < 100:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                if palign < 0.8 or pident < 0.8:
                                    continue
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpintronAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newintronAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = annotation_hg18_megatest
import unittest
from testlib import testutil, PygrTestProgram

import ConfigParser
import os
import string
import sys

from pygr.mapping import Collection
import pygr.Data

try:
    import hashlib
except ImportError:
    import md5 as hashlib

config = ConfigParser.ConfigParser({'testOutputBaseDir': '.',
                                    'smallSampleKey': ''})
config.read([os.path.join(os.path.expanduser('~'), '.pygrrc'),
             os.path.join(os.path.expanduser('~'), 'pygr.cfg'),
             '.pygrrc', 'pygr.cfg'])
msaDir = config.get('megatests_hg18', 'msaDir')
seqDir = config.get('megatests_hg18', 'seqDir')
smallSampleKey = config.get('megatests_hg18', 'smallSampleKey')
testInputDB = config.get('megatests', 'testInputDB')
testInputDir = config.get('megatests', 'testInputDir')
testOutputBaseDir = config.get('megatests', 'testOutputBaseDir')

if smallSampleKey:
    smallSamplePostfix = '_' + smallSampleKey
else:
    smallSamplePostfix = ''

## msaDir CONTAINS PRE-BUILT NLMSA
## seqDir CONTAINS GENOME ASSEMBLIES AND THEIR SEQDB FILES
## TEST INPUT/OUPTUT FOR COMPARISON, THESE FILES SHOULD BE IN THIS DIRECTORY
##        exonAnnotFileName = 'Annotation_ConservedElement_Exons_hg18.txt'
##        intronAnnotFileName = 'Annotation_ConservedElement_Introns_hg18.txt'
##        stopAnnotFileName = 'Annotation_ConservedElement_Stop_hg18.txt'
## testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList)) SHOULD
## BE DELETED IF YOU WANT TO RUN IN '.'

# DIRECTIONARY FOR DOC STRING OF SEQDB
docStringDict = {
    'anoCar1': 'Lizard Genome (January 2007)',
    'bosTau3': 'Cow Genome (August 2006)',
    'canFam2': 'Dog Genome (May 2005)',
    'cavPor2': 'Guinea Pig (October 2005)',
    'danRer4': 'Zebrafish Genome (March 2006)',
    'dasNov1': 'Armadillo Genome (May 2005)',
    'echTel1': 'Tenrec Genome (July 2005)',
    'eriEur1': 'European Hedgehog (Junuary 2006)',
    'equCab1': 'Horse Genome (January 2007)',
    'felCat3': 'Cat Genome (March 2006)',
    'fr2': 'Fugu Genome (October 2004)',
    'galGal3': 'Chicken Genome (May 2006)',
    'gasAcu1': 'Stickleback Genome (February 2006)',
    'hg18': 'Human Genome (May 2006)',
    'loxAfr1': 'Elephant Genome (May 2005)',
    'mm8': 'Mouse Genome (March 2006)',
    'monDom4': 'Opossum Genome (January 2006)',
    'ornAna1': 'Platypus Genome (March 2007)',
    'oryCun1': 'Rabbit Genome (May 2005)',
    'oryLat1': 'Medaka Genome (April 2006)',
    'otoGar1': 'Bushbaby Genome (December 2006)',
    'panTro2': 'Chimpanzee Genome (March 2006)',
    'rheMac2': 'Rhesus Genome (January 2006)',
    'rn4': 'Rat Genome (November 2004)',
    'sorAra1': 'Shrew (Junuary 2006)',
    'tetNig1': 'Tetraodon Genome (February 2004)',
    'tupBel1': 'Tree Shrew (December 2006)',
    'xenTro2': 'X. tropicalis Genome (August 2005)',
    }

# GENOME ASSEMBLY LIST FOR DM2 MULTIZ15WAY
msaSpeciesList = ['anoCar1', 'bosTau3', 'canFam2', 'cavPor2', 'danRer4',
                  'dasNov1', 'echTel1', 'equCab1', 'eriEur1', 'felCat3', 'fr2',
                  'galGal3', 'gasAcu1', 'hg18', 'loxAfr1', 'mm8', 'monDom4',
                  'ornAna1', 'oryCun1', 'oryLat1', 'otoGar1', 'panTro2',
                  'rheMac2', 'rn4', 'sorAra1', 'tetNig1', 'tupBel1', 'xenTro2']


class PygrBuildNLMSAMegabase(unittest.TestCase):

    def setUp(self, testDir=None):
        '''restrict megatest to an initially empty directory, need
        large space to perform'''
        import random
        tmpList = [c for c in 'PygrBuildNLMSAMegabase']
        random.shuffle(tmpList)
        # Comment out the next line to run in current directory.
        testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList))
        if testDir is None:
            testDir = 'TEST_' + ''.join(tmpList)
        try:
            os.mkdir(testDir)
            testDir = os.path.realpath(testDir)
        except:
            raise IOError
        self.path = testDir
        try:
            tmpFileName = os.path.join(testDir, 'DELETE_THIS_TEMP_FILE')
            open(tmpFileName, 'w').write('A' * 1024 * 1024)
        except:
            raise IOError
        pygr.Data.update(self.path)
        from pygr import seqdb
        for orgstr in msaSpeciesList:
            genome = seqdb.BlastDB(os.path.join(seqDir, orgstr))
            genome.__doc__ = docStringDict[orgstr]
            pygr.Data.addResource('TEST.Seq.Genome.' + orgstr, genome)
        pygr.Data.save()

    def copyFile(self, filename): # COPY A FILE INTO TEST DIRECTORY
        newname = os.path.join(self.path, os.path.basename(filename))
        open(newname, 'w').write(open(filename, 'r').read())
        return newname

    def tearDown(self):
        'delete the temporary directory and files, restore pygr.Data path'
        # Delete them bottom-up for obvious reasons.
        for dirpath, subdirs, files in os.walk(self.path, topdown=False):
            # Note: this part may not work in directories on NFS due to
            # creation of lock files (.nfsXXXXXXXXX), which will only allow
            # deletion after pygr.Data has been closed.
            for filename in files:
                os.remove(os.path.join(dirpath, filename))
            os.rmdir(dirpath)
        # Restore original pygr.Data path to remedy lack of isolation
        # between tests from the same run
        pygr.Data.update(None)


class Build_Test(PygrBuildNLMSAMegabase):

    def test_seqdb(self):
        'Check pygr.Data contents'
        l = pygr.Data.dir('TEST')
        preList = ['TEST.Seq.Genome.' + orgstr for orgstr in msaSpeciesList]
        assert l == preList

    def test_collectionannot(self):
        'Test building an AnnotationDB from file'
        from pygr import seqdb, cnestedlist, sqlgraph
        hg18 = pygr.Data.getResource('TEST.Seq.Genome.hg18')
        # BUILD ANNOTATION DATABASE FOR REFSEQ EXONS
        exon_slices = Collection(
            filename=os.path.join(self.path, 'refGene_exonAnnot_hg18.cdb'),
            intKeys=True, mode='cr', writeback=False)
        exon_db = seqdb.AnnotationDB(exon_slices, hg18,
                                     sliceAttrDict=dict(id=0, exon_id=1,
                                                        orientation=2,
                                                        gene_id=3, start=4,
                                                        stop=5))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_exonAnnot_hg18'), 'w',
                                pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir,
                                       'refGene_exonAnnot%s_hg18.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            exon_slices[row[1]] = row
            exon = exon_db[row[1]] # GET THE ANNOTATION OBJECT FOR THIS EXON
            msa.addAnnotation(exon) # SAVE IT TO GENOME MAPPING
        exon_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        exon_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        exon_db.__doc__ = 'Exon Annotation Database for hg18'
        pygr.Data.addResource('TEST.Annotation.hg18.exons', exon_db)
        msa.__doc__ = 'NLMSA Exon for hg18'
        pygr.Data.addResource('TEST.Annotation.NLMSA.hg18.exons', msa)
        exon_schema = pygr.Data.ManyToManyRelation(hg18, exon_db,
                                                   bindAttrs=('exon1', ))
        exon_schema.__doc__ = 'Exon Schema for hg18'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.hg18.exons', exon_schema)
        # BUILD ANNOTATION DATABASE FOR REFSEQ SPLICES
        splice_slices = Collection(
            filename=os.path.join(self.path, 'refGene_spliceAnnot_hg18.cdb'),
            intKeys=True, mode='cr', writeback=False)
        splice_db = seqdb.AnnotationDB(splice_slices, hg18,
                                       sliceAttrDict=dict(id=0, splice_id=1,
                                                          orientation=2,
                                                          gene_id=3, start=4,
                                                          stop=5))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_spliceAnnot_hg18'),
                                'w', pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir,
                                       'refGene_spliceAnnot%s_hg18.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            splice_slices[row[1]] = row
            # GET THE ANNOTATION OBJECT FOR THIS EXON
            splice = splice_db[row[1]]
            msa.addAnnotation(splice) # SAVE IT TO GENOME MAPPING
        splice_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        splice_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        splice_db.__doc__ = 'Splice Annotation Database for hg18'
        pygr.Data.addResource('TEST.Annotation.hg18.splices', splice_db)
        msa.__doc__ = 'NLMSA Splice for hg18'
        pygr.Data.addResource('TEST.Annotation.NLMSA.hg18.splices', msa)
        splice_schema = pygr.Data.ManyToManyRelation(hg18, splice_db,
                                                     bindAttrs=('splice1', ))
        splice_schema.__doc__ = 'Splice Schema for hg18'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.hg18.splices',
                            splice_schema)
        # BUILD ANNOTATION DATABASE FOR REFSEQ EXONS
        cds_slices = Collection(
            filename=os.path.join(self.path, 'refGene_cdsAnnot_hg18.cdb'),
            intKeys=True, mode='cr', writeback=False)
        cds_db = seqdb.AnnotationDB(cds_slices, hg18,
                                    sliceAttrDict=dict(id=0, cds_id=1,
                                                       orientation=2,
                                                       gene_id=3, start=4,
                                                       stop=5))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_cdsAnnot_hg18'), 'w',
                                pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir,
                                       'refGene_cdsAnnot%s_hg18.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            cds_slices[row[1]] = row
            cds = cds_db[row[1]] # GET THE ANNOTATION OBJECT FOR THIS EXON
            msa.addAnnotation(cds) # SAVE IT TO GENOME MAPPING
        cds_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        cds_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        cds_db.__doc__ = 'CDS Annotation Database for hg18'
        pygr.Data.addResource('TEST.Annotation.hg18.cdss', cds_db)
        msa.__doc__ = 'NLMSA CDS for hg18'
        pygr.Data.addResource('TEST.Annotation.NLMSA.hg18.cdss', msa)
        cds_schema = pygr.Data.ManyToManyRelation(hg18, cds_db,
                                                  bindAttrs=('cds1', ))
        cds_schema.__doc__ = 'CDS Schema for hg18'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.hg18.cdss', cds_schema)
        # BUILD ANNOTATION DATABASE FOR MOST CONSERVED ELEMENTS FROM UCSC
        ucsc_slices = Collection(
           filename=os.path.join(self.path, 'phastConsElements28way_hg18.cdb'),
            intKeys=True, mode='cr', writeback=False)
        ucsc_db = seqdb.AnnotationDB(ucsc_slices, hg18,
                                     sliceAttrDict=dict(id=0, ucsc_id=1,
                                                        orientation=2,
                                                        gene_id=3, start=4,
                                                        stop=5))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'phastConsElements28way_hg18'),
                                'w', pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir,
                                       'phastConsElements28way%s_hg18.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            ucsc_slices[row[1]] = row
            ucsc = ucsc_db[row[1]] # GET THE ANNOTATION OBJECT FOR THIS EXON
            msa.addAnnotation(ucsc) # SAVE IT TO GENOME MAPPING
        ucsc_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        ucsc_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        ucsc_db.__doc__ = 'Most Conserved Elements for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.hg18.mostconserved',
                              ucsc_db)
        msa.__doc__ = 'NLMSA for Most Conserved Elements for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.NLMSA.hg18.mostconserved',
                              msa)
        ucsc_schema = pygr.Data.ManyToManyRelation(hg18, ucsc_db,
                                                   bindAttrs=('element1', ))
        ucsc_schema.__doc__ = \
                'Schema for UCSC Most Conserved Elements for hg18'
        pygr.Data.addSchema('TEST.Annotation.UCSC.NLMSA.hg18.mostconserved',
                            ucsc_schema)
        # BUILD ANNOTATION DATABASE FOR SNP126 FROM UCSC
        snp_slices = Collection(filename=os.path.join(self.path,
                                                      'snp126_hg18.cdb'),
                                intKeys=True, protocol=2, mode='cr',
                                writeback=False)
        snp_db = seqdb.AnnotationDB(snp_slices, hg18,
                                    sliceAttrDict=dict(id=0, snp_id=1,
                                                       orientation=2,
                                                       gene_id=3, start=4,
                                                       stop=5, score=6,
                                                       ref_NCBI=7, ref_UCSC=8,
                                                       observed=9, molType=10,
                                                       myClass=11, myValid=12,
                                                       avHet=13, avHetSE=14,
                                                       myFunc=15, locType=16,
                                                       myWeight=17))
        msa = cnestedlist.NLMSA(os.path.join(self.path, 'snp126_hg18'), 'w',
                                pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir, 'snp126%s_hg18.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            snp_slices[row[1]] = row
            snp = snp_db[row[1]] # GET THE ANNOTATION OBJECT FOR THIS EXON
            msa.addAnnotation(snp) # SAVE IT TO GENOME MAPPING
        snp_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        snp_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        snp_db.__doc__ = 'SNP126 for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.hg18.snp126', snp_db)
        msa.__doc__ = 'NLMSA for SNP126 for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.NLMSA.hg18.snp126', msa)
        snp_schema = pygr.Data.ManyToManyRelation(hg18, snp_db,
                                                  bindAttrs=('snp1', ))
        snp_schema.__doc__ = 'Schema for UCSC SNP126 for hg18'
        pygr.Data.addSchema('TEST.Annotation.UCSC.NLMSA.hg18.snp126',
                            snp_schema)
        pygr.Data.save()
        pygr.Data.clear_cache()

        # QUERY TO EXON AND SPLICES ANNOTATION DATABASE
        hg18 = pygr.Data.getResource('TEST.Seq.Genome.hg18')
        exonmsa = pygr.Data.getResource('TEST.Annotation.NLMSA.hg18.exons')
        splicemsa = pygr.Data.getResource('TEST.Annotation.NLMSA.hg18.splices')
        conservedmsa = \
         pygr.Data.getResource('TEST.Annotation.UCSC.NLMSA.hg18.mostconserved')
        snpmsa = \
                pygr.Data.getResource('TEST.Annotation.UCSC.NLMSA.hg18.snp126')
        cdsmsa = pygr.Data.getResource('TEST.Annotation.NLMSA.hg18.cdss')
        exons = pygr.Data.getResource('TEST.Annotation.hg18.exons')
        splices = pygr.Data.getResource('TEST.Annotation.hg18.splices')
        mostconserved = \
               pygr.Data.getResource('TEST.Annotation.UCSC.hg18.mostconserved')
        snp126 = pygr.Data.getResource('TEST.Annotation.UCSC.hg18.snp126')
        cdss = pygr.Data.getResource('TEST.Annotation.hg18.cdss')

        # OPEN hg18_MULTIZ28WAY NLMSA
        msa = cnestedlist.NLMSA(os.path.join(msaDir, 'hg18_multiz28way'), 'r',
                                trypath=[seqDir])

        exonAnnotFileName = os.path.join(testInputDir,
                                 'Annotation_ConservedElement_Exons%s_hg18.txt'
                                         % smallSamplePostfix)
        intronAnnotFileName = os.path.join(testInputDir,
                               'Annotation_ConservedElement_Introns%s_hg18.txt'
                                           % smallSamplePostfix)
        stopAnnotFileName = os.path.join(testInputDir,
                                  'Annotation_ConservedElement_Stop%s_hg18.txt'
                                         % smallSamplePostfix)
        newexonAnnotFileName = os.path.join(self.path, 'new_Exons_hg18.txt')
        newintronAnnotFileName = os.path.join(self.path,
                                              'new_Introns_hg18.txt')
        newstopAnnotFileName = os.path.join(self.path, 'new_stop_hg18.txt')
        tmpexonAnnotFileName = self.copyFile(exonAnnotFileName)
        tmpintronAnnotFileName = self.copyFile(intronAnnotFileName)
        tmpstopAnnotFileName = self.copyFile(stopAnnotFileName)

        if smallSampleKey:
            chrList = [smallSampleKey]
        else:
            chrList = hg18.seqLenDict.keys()
            chrList.sort()

        outfile = open(newexonAnnotFileName, 'w')
        for chrid in chrList:
            slice = hg18[chrid]
            # EXON ANNOTATION DATABASE
            try:
                ex1 = exonmsa[slice]
            except:
                continue
            else:
                exlist1 = [(ix.exon_id, ix) for ix in ex1.keys()]
                exlist1.sort()
                for ixx, exon in exlist1:
                    saveList = []
                    tmp = exon.sequence
                    tmpexon = exons[exon.exon_id]
                    tmpslice = tmpexon.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'EXON', chrid, tmpexon.exon_id, tmpexon.gene_id, \
                            tmpslice.start, tmpslice.stop
                    try:
                        out1 = conservedmsa[tmp]
                    except KeyError:
                        pass
                    else:
                        elementlist = [(ix.ucsc_id, ix) for ix in out1.keys()]
                        elementlist.sort()
                        for iyy, element in elementlist:
                            if element.stop - element.start < 100:
                                continue
                            score = int(string.split(element.gene_id, '=')[1])
                            if score < 100:
                                continue
                            tmp2 = element.sequence
                            tmpelement = mostconserved[element.ucsc_id]
                            # FOR REAL ELEMENT COORDINATE
                            tmpslice2 = tmpelement.sequence
                            wlist2 = wlist1 + (tmpelement.ucsc_id,
                                               tmpelement.gene_id,
                                               tmpslice2.start,
                                               tmpslice2.stop)
                            slicestart, sliceend = max(tmp.start, tmp2.start),\
                                    min(tmp.stop, tmp2.stop)
                            if slicestart < 0 or sliceend < 0:
                                sys.exit('wrong query')
                            tmp1 = msa.seqDict['hg18.' + chrid][slicestart:
                                                                sliceend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start < 100:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                if palign < 0.8 or pident < 0.8:
                                    continue
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpexonAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newexonAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

        outfile = open(newintronAnnotFileName, 'w')
        for chrid in chrList:
            slice = hg18[chrid]
            # SPLICE ANNOTATION DATABASE
            try:
                sp1 = splicemsa[slice]
            except:
                continue
            else:
                splist1 = [(ix.splice_id, ix) for ix in sp1.keys()]
                splist1.sort()
                for ixx, splice in splist1:
                    saveList = []
                    tmp = splice.sequence
                    tmpsplice = splices[splice.splice_id]
                    tmpslice = tmpsplice.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'INTRON', chrid, tmpsplice.splice_id, \
                            tmpsplice.gene_id, tmpslice.start, tmpslice.stop
                    try:
                        out1 = conservedmsa[tmp]
                    except KeyError:
                        pass
                    else:
                        elementlist = [(ix.ucsc_id, ix) for ix in out1.keys()]
                        elementlist.sort()
                        for iyy, element in elementlist:
                            if element.stop - element.start < 100:
                                continue
                            score = int(string.split(element.gene_id, '=')[1])
                            if score < 100:
                                continue
                            tmp2 = element.sequence
                            tmpelement = mostconserved[element.ucsc_id]
                            # FOR REAL ELEMENT COORDINATE
                            tmpslice2 = tmpelement.sequence
                            wlist2 = wlist1 + (tmpelement.ucsc_id,
                                               tmpelement.gene_id,
                                               tmpslice2.start,
                                               tmpslice2.stop)
                            slicestart, sliceend = max(tmp.start, tmp2.start),\
                                    min(tmp.stop, tmp2.stop)
                            if slicestart < 0 or sliceend < 0:
                                sys.exit('wrong query')
                            tmp1 = msa.seqDict['hg18.' + chrid][slicestart:
                                                                sliceend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start < 100:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                if palign < 0.8 or pident < 0.8:
                                    continue
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
                    # SNP IN SPLICE SITES
                    saveList = []
                    gt = tmpslice[:2]
                    ag = tmpslice[-2:]
                    try:
                        gtout = snpmsa[gt]
                        agout = snpmsa[ag]
                    except KeyError:
                        pass
                    else:
                        gtlist = gtout.keys()
                        aglist = agout.keys()
                        for snp in gtlist:
                            tmpsnp = snp.sequence
                            annsnp = snp126[snp.snp_id]
                            wlist2 = ('SNP5', chrid, tmpsplice.gene_id,
                                      gt.start, gt.stop, str(gt)) + \
                                    (annsnp.snp_id, tmpsnp.start, tmpsnp.stop,
                                     str(tmpsnp), annsnp.gene_id,
                                     annsnp.ref_NCBI, annsnp.ref_UCSC,
                                     annsnp.observed, annsnp.molType,
                                     annsnp.myClass, annsnp.myValid)
                            tmp1 = msa.seqDict['hg18.' + chrid][abs(gt.start):\
                                                                abs(gt.stop)]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start != 2 or \
                                   dest.stop - dest.start != 2:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        for snp in aglist:
                            tmpsnp = snp.sequence
                            annsnp = snp126[snp.snp_id]
                            wlist2 = ('SNP3', chrid, tmpsplice.gene_id,
                                      ag.start, ag.stop, str(ag)) + \
                                    (annsnp.snp_id, tmpsnp.start, tmpsnp.stop,
                                     str(tmpsnp), annsnp.gene_id,
                                     annsnp.ref_NCBI, annsnp.ref_UCSC,
                                     annsnp.observed, annsnp.molType,
                                     annsnp.myClass, annsnp.myValid)
                            tmp1 = msa.seqDict['hg18.' + chrid][abs(ag.start):\
                                                                abs(ag.stop)]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start != 2 or \
                                   dest.stop - dest.start != 2:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpintronAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newintronAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

        outfile = open(newstopAnnotFileName, 'w')
        for chrid in chrList:
            slice = hg18[chrid]
            # STOP ANNOTATION DATABASE
            try:
                cds1 = cdsmsa[slice]
            except:
                continue
            else:
                cdslist1 = [(ix.cds_id, ix) for ix in cds1.keys()]
                cdslist1.sort()
                for ixx, cds in cdslist1:
                    saveList = []
                    tmp = cds.sequence
                    tmpcds = cdss[cds.cds_id]
                    tmpslice = tmpcds.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'STOP', chrid, tmpcds.cds_id, tmpcds.gene_id, \
                            tmpslice.start, tmpslice.stop
                    if tmpslice.start < 0:
                        stopstart, stopend = -tmpslice.stop, -tmpslice.start
                        stop = -hg18[chrid][stopstart:stopstart+3]
                    else:
                        stopstart, stopend = tmpslice.start, tmpslice.stop
                        stop = hg18[chrid][stopend-3:stopend]
                    if str(stop).upper() not in ('TAA', 'TAG', 'TGA'):
                        continue
                    try:
                        snp1 = snpmsa[stop]
                    except KeyError:
                        pass
                    else:
                        snplist = [(ix.snp_id, ix) for ix in snp1.keys()]
                        snplist.sort()
                        for iyy, snp in snplist:
                            tmpsnp = snp.sequence
                            annsnp = snp126[snp.snp_id]
                            wlist2 = wlist1 + (str(stop), stop.start,
                                               stop.stop) + \
                                    (annsnp.snp_id, tmpsnp.start, tmpsnp.stop,
                                     str(tmpsnp), annsnp.gene_id,
                                     annsnp.ref_NCBI, annsnp.ref_UCSC,
                                     annsnp.observed, annsnp.molType,
                                     annsnp.myClass, annsnp.myValid)
                            if tmpslice.start < 0:
                                tmp1 = -msa.seqDict['hg18.' + chrid]\
                                        [stopstart:stopstart + 3]
                            else:
                                tmp1 = msa.seqDict['hg18.' + chrid]\
                                        [stopend - 3:stopend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start != 3 or \
                                   dest.stop - dest.start != 3:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                if str(dest).upper() not in ('TAA', 'TAG',
                                                             'TGA'):
                                    nonstr = 'NONSENSE'
                                else:
                                    nonstr = 'STOP'
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident,
                                                   nonstr)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpstopAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newstopAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

    def test_mysqlannot(self):
        'Test building an AnnotationDB from MySQL'
        from pygr import seqdb, cnestedlist, sqlgraph
        hg18 = pygr.Data.getResource('TEST.Seq.Genome.hg18')
        # BUILD ANNOTATION DATABASE FOR REFSEQ EXONS: MYSQL VERSION
        exon_slices = sqlgraph.SQLTableClustered(
            '%s.pygr_refGene_exonAnnot%s_hg18' % (testInputDB,
                                                  smallSamplePostfix),
            clusterKey='chromosome', maxCache=0)
        exon_db = seqdb.AnnotationDB(exon_slices, hg18,
                                     sliceAttrDict=dict(id='chromosome',
                                                        gene_id='name',
                                                        exon_id='exon_id'))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_exonAnnot_SQL_hg18'),
                                'w', pairwiseMode=True, bidirectional=False)
        for id in exon_db:
            msa.addAnnotation(exon_db[id])
        exon_db.clear_cache() # not really necessary; cache should autoGC
        exon_slices.clear_cache()
        msa.build()
        exon_db.__doc__ = 'SQL Exon Annotation Database for hg18'
        pygr.Data.addResource('TEST.Annotation.SQL.hg18.exons', exon_db)
        msa.__doc__ = 'SQL NLMSA Exon for hg18'
        pygr.Data.addResource('TEST.Annotation.NLMSA.SQL.hg18.exons', msa)
        exon_schema = pygr.Data.ManyToManyRelation(hg18, exon_db,
                                                   bindAttrs=('exon2', ))
        exon_schema.__doc__ = 'SQL Exon Schema for hg18'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.SQL.hg18.exons',
                            exon_schema)
        # BUILD ANNOTATION DATABASE FOR REFSEQ SPLICES: MYSQL VERSION
        splice_slices = sqlgraph.SQLTableClustered(
            '%s.pygr_refGene_spliceAnnot%s_hg18' % (testInputDB,
                                                    smallSamplePostfix),
            clusterKey='chromosome', maxCache=0)
        splice_db = seqdb.AnnotationDB(splice_slices, hg18,
                                       sliceAttrDict=dict(id='chromosome',
                                                          gene_id='name',
                                                        splice_id='splice_id'))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_spliceAnnot_SQL_hg18'),
                                'w', pairwiseMode=True, bidirectional=False)
        for id in splice_db:
            msa.addAnnotation(splice_db[id])
        splice_db.clear_cache() # not really necessary; cache should autoGC
        splice_slices.clear_cache()
        msa.build()
        splice_db.__doc__ = 'SQL Splice Annotation Database for hg18'
        pygr.Data.addResource('TEST.Annotation.SQL.hg18.splices', splice_db)
        msa.__doc__ = 'SQL NLMSA Splice for hg18'
        pygr.Data.addResource('TEST.Annotation.NLMSA.SQL.hg18.splices', msa)
        splice_schema = pygr.Data.ManyToManyRelation(hg18, splice_db,
                                                     bindAttrs=('splice2', ))
        splice_schema.__doc__ = 'SQL Splice Schema for hg18'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.SQL.hg18.splices',
                            splice_schema)
        # BUILD ANNOTATION DATABASE FOR REFSEQ EXONS: MYSQL VERSION
        cds_slices = sqlgraph.SQLTableClustered(
            '%s.pygr_refGene_cdsAnnot%s_hg18' % (testInputDB,
                                                 smallSamplePostfix),
            clusterKey='chromosome', maxCache=0)
        cds_db = seqdb.AnnotationDB(cds_slices, hg18,
                                    sliceAttrDict=dict(id='chromosome',
                                                       gene_id='name',
                                                       cds_id='cds_id'))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_cdsAnnot_SQL_hg18'), 'w',
                                pairwiseMode=True, bidirectional=False)
        for id in cds_db:
            msa.addAnnotation(cds_db[id])
        cds_db.clear_cache() # not really necessary; cache should autoGC
        cds_slices.clear_cache()
        msa.build()
        cds_db.__doc__ = 'SQL CDS Annotation Database for hg18'
        pygr.Data.addResource('TEST.Annotation.SQL.hg18.cdss', cds_db)
        msa.__doc__ = 'SQL NLMSA CDS for hg18'
        pygr.Data.addResource('TEST.Annotation.NLMSA.SQL.hg18.cdss', msa)
        cds_schema = pygr.Data.ManyToManyRelation(hg18, cds_db,
                                                  bindAttrs=('cds2', ))
        cds_schema.__doc__ = 'SQL CDS Schema for hg18'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.SQL.hg18.cdss', cds_schema)
        # BUILD ANNOTATION DATABASE FOR MOST CONSERVED ELEMENTS FROM UCSC:
        # MYSQL VERSION
        ucsc_slices = \
             sqlgraph.SQLTableClustered('%s.pygr_phastConsElements28way%s_hg18'
                                        % (testInputDB, smallSamplePostfix),
                                        clusterKey='chromosome', maxCache=0)
        ucsc_db = seqdb.AnnotationDB(ucsc_slices, hg18,
                                     sliceAttrDict=dict(id='chromosome',
                                                        gene_id='name',
                                                        ucsc_id='ucsc_id'))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                            'phastConsElements28way_SQL_hg18'),
                                'w', pairwiseMode=True, bidirectional=False)
        for id in ucsc_db:
            msa.addAnnotation(ucsc_db[id])
        ucsc_db.clear_cache() # not really necessary; cache should autoGC
        ucsc_slices.clear_cache()
        msa.build()
        ucsc_db.__doc__ = 'SQL Most Conserved Elements for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.SQL.hg18.mostconserved',
                              ucsc_db)
        msa.__doc__ = 'SQL NLMSA for Most Conserved Elements for hg18'
        pygr.Data.addResource(
            'TEST.Annotation.UCSC.NLMSA.SQL.hg18.mostconserved', msa)
        ucsc_schema = pygr.Data.ManyToManyRelation(hg18, ucsc_db,
                                                   bindAttrs=('element2', ))
        ucsc_schema.__doc__ = \
                'SQL Schema for UCSC Most Conserved Elements for hg18'
        pygr.Data.addSchema(
            'TEST.Annotation.UCSC.NLMSA.SQL.hg18.mostconserved', ucsc_schema)
        # BUILD ANNOTATION DATABASE FOR SNP126 FROM UCSC: MYSQL VERSION
        snp_slices = sqlgraph.SQLTableClustered('%s.pygr_snp126%s_hg18'
                                                % (testInputDB,
                                                   smallSamplePostfix),
                                                clusterKey='clusterKey',
                                                maxCache=0)
        snp_db = seqdb.AnnotationDB(snp_slices, hg18,
                                    sliceAttrDict=dict(id='chromosome',
                                                       gene_id='name',
                                                       snp_id='snp_id',
                                                       score='score',
                                                       ref_NCBI='ref_NCBI',
                                                       ref_UCSC='ref_UCSC',
                                                       observed='observed',
                                                       molType='molType',
                                                       myClass='myClass',
                                                       myValid='myValid',
                                                       avHet='avHet',
                                                       avHetSE='avHetSE',
                                                       myFunc='myFunc',
                                                       locType='locType',
                                                       myWeight='myWeight'))
        msa = cnestedlist.NLMSA(os.path.join(self.path, 'snp126_SQL_hg18'),
                                'w', pairwiseMode=True, bidirectional=False)
        for id in snp_db:
            msa.addAnnotation(snp_db[id])
        snp_db.clear_cache() # not really necessary; cache should autoGC
        snp_slices.clear_cache()
        msa.build()
        snp_db.__doc__ = 'SQL SNP126 for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.SQL.hg18.snp126', snp_db)
        msa.__doc__ = 'SQL NLMSA for SNP126 for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.NLMSA.SQL.hg18.snp126',
                              msa)
        snp_schema = pygr.Data.ManyToManyRelation(hg18, snp_db,
                                                  bindAttrs=('snp2', ))
        snp_schema.__doc__ = 'SQL Schema for UCSC SNP126 for hg18'
        pygr.Data.addSchema('TEST.Annotation.UCSC.NLMSA.SQL.hg18.snp126',
                            snp_schema)
        pygr.Data.save()
        pygr.Data.clear_cache()

        # QUERY TO EXON AND SPLICES ANNOTATION DATABASE
        hg18 = pygr.Data.getResource('TEST.Seq.Genome.hg18')
        exonmsa = pygr.Data.getResource('TEST.Annotation.NLMSA.SQL.hg18.exons')
        splicemsa = \
                pygr.Data.getResource('TEST.Annotation.NLMSA.SQL.hg18.splices')
        conservedmsa = \
     pygr.Data.getResource('TEST.Annotation.UCSC.NLMSA.SQL.hg18.mostconserved')
        snpmsa = \
            pygr.Data.getResource('TEST.Annotation.UCSC.NLMSA.SQL.hg18.snp126')
        cdsmsa = pygr.Data.getResource('TEST.Annotation.NLMSA.SQL.hg18.cdss')
        exons = pygr.Data.getResource('TEST.Annotation.SQL.hg18.exons')
        splices = pygr.Data.getResource('TEST.Annotation.SQL.hg18.splices')
        mostconserved = \
           pygr.Data.getResource('TEST.Annotation.UCSC.SQL.hg18.mostconserved')
        snp126 = pygr.Data.getResource('TEST.Annotation.UCSC.SQL.hg18.snp126')
        cdss = pygr.Data.getResource('TEST.Annotation.SQL.hg18.cdss')

        # OPEN hg18_MULTIZ28WAY NLMSA
        msa = cnestedlist.NLMSA(os.path.join(msaDir, 'hg18_multiz28way'), 'r',
                                trypath=[seqDir])

        exonAnnotFileName = os.path.join(testInputDir,
                                 'Annotation_ConservedElement_Exons%s_hg18.txt'
                                         % smallSamplePostfix)
        intronAnnotFileName = os.path.join(testInputDir,
                               'Annotation_ConservedElement_Introns%s_hg18.txt'
                                           % smallSamplePostfix)
        stopAnnotFileName = os.path.join(testInputDir,
                                  'Annotation_ConservedElement_Stop%s_hg18.txt'
                                         % smallSamplePostfix)
        newexonAnnotFileName = os.path.join(self.path, 'new_Exons_hg18.txt')
        newintronAnnotFileName = os.path.join(self.path,
                                              'new_Introns_hg18.txt')
        newstopAnnotFileName = os.path.join(self.path, 'new_stop_hg18.txt')
        tmpexonAnnotFileName = self.copyFile(exonAnnotFileName)
        tmpintronAnnotFileName = self.copyFile(intronAnnotFileName)
        tmpstopAnnotFileName = self.copyFile(stopAnnotFileName)

        if smallSampleKey:
            chrList = [smallSampleKey]
        else:
            chrList = hg18.seqLenDict.keys()
            chrList.sort()

        outfile = open(newexonAnnotFileName, 'w')
        for chrid in chrList:
            slice = hg18[chrid]
            # EXON ANNOTATION DATABASE
            try:
                ex1 = exonmsa[slice]
            except:
                continue
            else:
                exlist1 = [(ix.exon_id, ix) for ix in ex1.keys()]
                exlist1.sort()
                for ixx, exon in exlist1:
                    saveList = []
                    tmp = exon.sequence
                    tmpexon = exons[exon.exon_id]
                    tmpslice = tmpexon.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'EXON', chrid, tmpexon.exon_id, tmpexon.gene_id, \
                            tmpslice.start, tmpslice.stop
                    try:
                        out1 = conservedmsa[tmp]
                    except KeyError:
                        pass
                    else:
                        elementlist = [(ix.ucsc_id, ix) for ix in out1.keys()]
                        elementlist.sort()
                        for iyy, element in elementlist:
                            if element.stop - element.start < 100:
                                continue
                            score = int(string.split(element.gene_id, '=')[1])
                            if score < 100:
                                continue
                            tmp2 = element.sequence
                            tmpelement = mostconserved[element.ucsc_id]
                            # FOR REAL ELEMENT COORDINATE
                            tmpslice2 = tmpelement.sequence
                            wlist2 = wlist1 + (tmpelement.ucsc_id,
                                               tmpelement.gene_id,
                                               tmpslice2.start,
                                               tmpslice2.stop)
                            slicestart, sliceend = max(tmp.start, tmp2.start),\
                                    min(tmp.stop, tmp2.stop)
                            if slicestart < 0 or sliceend < 0:
                                sys.exit('wrong query')
                            tmp1 = msa.seqDict['hg18.' + chrid][slicestart:
                                                                sliceend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start < 100:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                if palign < 0.8 or pident < 0.8:
                                    continue
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpexonAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newexonAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

        outfile = open(newintronAnnotFileName, 'w')
        for chrid in chrList:
            slice = hg18[chrid]
            # SPLICE ANNOTATION DATABASE
            try:
                sp1 = splicemsa[slice]
            except:
                continue
            else:
                splist1 = [(ix.splice_id, ix) for ix in sp1.keys()]
                splist1.sort()
                for ixx, splice in splist1:
                    saveList = []
                    tmp = splice.sequence
                    tmpsplice = splices[splice.splice_id]
                    tmpslice = tmpsplice.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'INTRON', chrid, tmpsplice.splice_id, \
                            tmpsplice.gene_id, tmpslice.start, tmpslice.stop
                    try:
                        out1 = conservedmsa[tmp]
                    except KeyError:
                        pass
                    else:
                        elementlist = [(ix.ucsc_id, ix) for ix in out1.keys()]
                        elementlist.sort()
                        for iyy, element in elementlist:
                            if element.stop - element.start < 100:
                                continue
                            score = int(string.split(element.gene_id, '=')[1])
                            if score < 100:
                                continue
                            tmp2 = element.sequence
                            tmpelement = mostconserved[element.ucsc_id]
                            # FOR REAL ELEMENT COORDINATE
                            tmpslice2 = tmpelement.sequence
                            wlist2 = wlist1 + (tmpelement.ucsc_id,
                                               tmpelement.gene_id,
                                               tmpslice2.start,
                                               tmpslice2.stop)
                            slicestart, sliceend = max(tmp.start, tmp2.start),\
                                    min(tmp.stop, tmp2.stop)
                            if slicestart < 0 or sliceend < 0:
                                sys.exit('wrong query')
                            tmp1 = msa.seqDict['hg18.' + chrid][slicestart:
                                                                sliceend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start < 100:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                if palign < 0.8 or pident < 0.8:
                                    continue
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
                    # SNP IN SPLICE SITES
                    saveList = []
                    gt = tmpslice[:2]
                    ag = tmpslice[-2:]
                    try:
                        gtout = snpmsa[gt]
                        agout = snpmsa[ag]
                    except KeyError:
                        pass
                    else:
                        gtlist = gtout.keys()
                        aglist = agout.keys()
                        for snp in gtlist:
                            tmpsnp = snp.sequence
                            annsnp = snp126[snp.snp_id]
                            wlist2 = ('SNP5', chrid, tmpsplice.gene_id,
                                      gt.start, gt.stop, str(gt)) + \
                                    (annsnp.snp_id, tmpsnp.start, tmpsnp.stop,
                                     str(tmpsnp), annsnp.gene_id,
                                     annsnp.ref_NCBI, annsnp.ref_UCSC,
                                     annsnp.observed, annsnp.molType,
                                     annsnp.myClass, annsnp.myValid)
                            tmp1 = msa.seqDict['hg18.' + chrid][abs(gt.start):
                                                                abs(gt.stop)]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start != 2 or \
                                   dest.stop - dest.start != 2:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        for snp in aglist:
                            tmpsnp = snp.sequence
                            annsnp = snp126[snp.snp_id]
                            wlist2 = ('SNP3', chrid, tmpsplice.gene_id,
                                      ag.start, ag.stop, str(ag)) + \
                                    (annsnp.snp_id, tmpsnp.start, tmpsnp.stop,
                                     str(tmpsnp), annsnp.gene_id,
                                     annsnp.ref_NCBI, annsnp.ref_UCSC,
                                     annsnp.observed, annsnp.molType,
                                     annsnp.myClass, annsnp.myValid)
                            tmp1 = msa.seqDict['hg18.' + chrid][abs(ag.start):
                                                                abs(ag.stop)]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start != 2 or \
                                   dest.stop - dest.start != 2:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpintronAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newintronAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

        outfile = open(newstopAnnotFileName, 'w')
        for chrid in chrList:
            slice = hg18[chrid]
            # STOP ANNOTATION DATABASE
            try:
                cds1 = cdsmsa[slice]
            except:
                continue
            else:
                cdslist1 = [(ix.cds_id, ix) for ix in cds1.keys()]
                cdslist1.sort()
                for ixx, cds in cdslist1:
                    saveList = []
                    tmp = cds.sequence
                    tmpcds = cdss[cds.cds_id]
                    tmpslice = tmpcds.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'STOP', chrid, tmpcds.cds_id, tmpcds.gene_id, \
                            tmpslice.start, tmpslice.stop
                    if tmpslice.start < 0:
                        stopstart, stopend = -tmpslice.stop, -tmpslice.start
                        stop = -hg18[chrid][stopstart:stopstart+3]
                    else:
                        stopstart, stopend = tmpslice.start, tmpslice.stop
                        stop = hg18[chrid][stopend-3:stopend]
                    if str(stop).upper() not in ('TAA', 'TAG', 'TGA'):
                        continue
                    try:
                        snp1 = snpmsa[stop]
                    except KeyError:
                        pass
                    else:
                        snplist = [(ix.snp_id, ix) for ix in snp1.keys()]
                        snplist.sort()
                        for iyy, snp in snplist:
                            tmpsnp = snp.sequence
                            annsnp = snp126[snp.snp_id]
                            wlist2 = wlist1 + (str(stop), stop.start,
                                               stop.stop) + (annsnp.snp_id,
                                                             tmpsnp.start,
                                                             tmpsnp.stop,
                                                             str(tmpsnp),
                                                             annsnp.gene_id,
                                                             annsnp.ref_NCBI,
                                                             annsnp.ref_UCSC,
                                                             annsnp.observed,
                                                             annsnp.molType,
                                                             annsnp.myClass,
                                                             annsnp.myValid)
                            if tmpslice.start < 0:
                                tmp1 = -msa.seqDict['hg18.' + chrid]\
                                        [stopstart:stopstart + 3]
                            else:
                                tmp1 = msa.seqDict['hg18.' + chrid]\
                                        [stopend - 3:stopend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start != 3 or \
                                   dest.stop - dest.start != 3:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                palign, pident = '%.2f' % palign, '%.2f' \
                                        % pident
                                if str(dest).upper() not in ('TAA', 'TAG',
                                                             'TGA'):
                                    nonstr = 'NONSENSE'
                                else:
                                    nonstr = 'STOP'
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident,
                                                   nonstr)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpstopAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newstopAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = annotation_test
import unittest
from testlib import testutil, PygrTestProgram
from pygr import sequence, seqdb, sequtil, annotation
from pygr.sequence import Sequence
from pygr.annotation import AnnotationDB


class AnnotationSeq_Test(unittest.TestCase):

    def setUp(self):

        class Annotation(object):

            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        slicedb = dict(X=Annotation(id='seq', start=0, stop=10),
                       Y=Annotation(id='seq', start=0, stop=10),
                       Z=Annotation(id='seq2', start=0, stop=10))

        sequence_dict = dict(seq = Sequence('ATGGGGCCGATTG', 'seq', ),
                             seq2 = Sequence('ATGGGGCCGATTG', 'seq2'))

        self.db = AnnotationDB(slicedb, sequence_dict)

        self.annot = self.db['X']

    def test_orientation_index_error(self):
        db = self.db
        db.sliceAttrDict = dict(id=0, start=1, stop=2, orientation=3)

        # index error should be caught silently, so this should succeed.
        db.new_annotation('some name', ('seq', 5, 8))

    def test_cache_size(self):
        'test stupid cache size bug'
        assert self.db._weakValueDict.n > 20

    def test_cmp(self):
        assert cmp(self.annot, None) == -1
        assert cmp(self.annot, self.annot) == 0

        a = self.annot
        b = self.annot

        assert cmp(a, b) == 0
        assert a[1:2] == b[1:2]

        # different annotations, even though they point at the same sequence
        assert cmp(self.annot, self.db['Y']) == -1

        # different sequences, even though they point at the same actual seq
        assert cmp(self.annot, self.db['Z']) == -1

    def test_strslice(self):
        try:
            str(self.annot)
            assert 0, "should not get here"
        except ValueError:
            pass

    def test_repr(self):
        annot = self.annot
        assert repr(annot) == 'annotX[0:10]'
        assert repr(-annot) == '-annotX[0:10]'

        annot.annotationType = 'foo'
        assert repr(annot) == 'fooX[0:10]'
        del annot.annotationType

    def test_seq(self):
        assert repr(self.annot.sequence) == 'seq[0:10]'

    def test_slice(self):
        assert repr(self.annot[1:2].sequence) == 'seq[1:2]'


class AnnotationDB_Test(unittest.TestCase):
    """
    Test for all of the basic dictionary functions on 'AnnotationDB'.
    """

    def setUp(self):

        class Annotation(object):

            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        slicedb = dict(annot1=Annotation(id='seq', start=0, stop=10),
                       annot2=Annotation(id='seq', start=5, stop=9))
        sequence_dict = dict(seq = Sequence('ATGGGGCCGATTG', 'seq'))
        self.db = AnnotationDB(slicedb, sequence_dict)

    def test_setitem(self):
        try:
            self.db['foo'] = 'bar'      # use 'add_annotation' instead
            assert 0, "should not reach this point"
        except KeyError:
            pass

    def test_hash(self):
        x = hash(self.db)               # works!
        d = dict(foo=self.db)           # also works!

    def test_keys(self):
        "AnnotationDB keys"
        k = self.db.keys()
        k.sort()
        assert k == ['annot1', 'annot2'], k

    def test_contains(self):
        "AnnotationDB contains"
        assert 'annot1' in self.db, self.db.keys()
        assert 'annot2' in self.db
        assert 'foo' not in self.db

    def test_has_key(self):
        "AnnotationDB has key"
        assert 'annot1' in self.db
        assert 'annot2' in self.db
        assert 'foo' not in self.db

    def test_get(self):
        "AnnotationDB get"
        assert self.db.get('foo') is None
        assert self.db.get('annot1') is not None
        assert str(self.db.get('annot1').sequence).startswith('ATGGGGC')
        assert self.db.get('annot2') is not None
        assert str(self.db.get('annot2').sequence).startswith('GCCG')

    def test_items(self):
        "AnnotationDB items"
        i = [k for (k, v) in self.db.items()]
        i.sort()
        assert i == ['annot1', 'annot2']

    def test_iterkeys(self):
        "AnnotationDB iterkeys"
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik

    def test_itervalues(self):
        "AnnotationDB itervalues"
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv[0] == iv[0]
        assert kv == iv, (kv, iv)

    def test_iteritems(self):
        "AnnotationDB iteritems"
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii, (ki, ii)

    def test_readonly(self):
        "AnnotationDB readonly"
        try:
            self.db.copy()              # what should 'copy' do on AD?
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:                           # what should 'setdefault' do on AD?
            self.db.setdefault('foo')
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:                           # what should 'update' do on AD?
            self.db.update({})
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.clear()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.pop()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.popitem()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass

    def test_equality(self):
        "AnnotationDB equality"
        # Check that separately generated annotation objects test equal"
        key = 'annot1'
        db = self.db
        x = db.sliceAnnotation(key, db.sliceDB[key])
        y = db.sliceAnnotation(key, db.sliceDB[key])
        assert x == y

    def test_bad_seqdict(self):
        "AnnotationDB bad seqdict"

        class Annotation(object):

            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        slicedb = dict(annot1=Annotation(id='seq', start=0, stop=10),
                       annot2=Annotation(id='seq', start=5, stop=9))
        foo_dict = dict(foo=Sequence('ATGGGGCCGATTG', 'foo'))
        try:
            db = AnnotationDB(slicedb, foo_dict)
            assert 0, "incorrect seqdb; key error should be raised"
        except KeyError:
            pass


class Translation_Test(unittest.TestCase):

    def setUp(self):
        self.M = sequence.Sequence('ATG', 'methionine')
        self.FLIM = sequence.Sequence('TTTCTAATTATG', 'flim')
        self.db = dict(methionine=self.M, flim=self.FLIM)

    def test_simple_translate(self):
        db = self.db

        assert sequtil.translate_orf(str(db['methionine'])) == 'M'
        assert sequtil.translate_orf(str(db['flim'])) == 'FLIM'

    def test_translation_db(self):
        aa_db = annotation.AnnotationDB({}, self.db,
                          itemClass=annotation.TranslationAnnot,
                          itemSliceClass=annotation.TranslationAnnotSlice,
                          sliceAttrDict=dict(id=0, start=1, stop=2))

        aa = aa_db.new_annotation('foo', (self.M.id, 0, 3))
        orf = aa_db['foo']
        assert str(orf) == 'M'

        aa2 = aa_db.new_annotation('bar', (self.FLIM.id, 0, 12))
        orf = aa_db['bar']
        assert str(orf) == 'FLIM'

    def test_slice_descr(self):
        aa_db = annotation.AnnotationDB({}, self.db,
                          itemClass=annotation.TranslationAnnot,
                          itemSliceClass=annotation.TranslationAnnotSlice,
                          sliceAttrDict=dict(id=0, start=1, stop=2))

        aa = aa_db.new_annotation('bar', (self.FLIM.id, 0, 12))
        assert str(aa) == 'FLIM'
        assert str(aa[1:3].sequence) == 'CTAATT'

    def test_positive_frames(self):
        aa_db = annotation.AnnotationDB({}, self.db,
                          itemClass=annotation.TranslationAnnot,
                          itemSliceClass=annotation.TranslationAnnotSlice,
                          sliceAttrDict=dict(id=0, start=1, stop=2))

        f1 = aa_db.new_annotation('f1', (self.FLIM.id, 0, 12))
        assert str(f1) == 'FLIM'
        assert f1.frame == +1

        f2 = aa_db.new_annotation('f2', (self.FLIM.id, 1, 10))
        assert str(f2) == 'F*L'
        assert f2.frame == +2

        f3 = aa_db.new_annotation('f3', (self.FLIM.id, 2, 11))
        assert str(f3) == 'SNY'
        assert f3.frame == +3

    def test_negative_frames(self):
        aa_db = annotation.AnnotationDB({}, self.db,
                          itemClass=annotation.TranslationAnnot,
                          itemSliceClass=annotation.TranslationAnnotSlice,
                          sliceAttrDict=dict(id=0, start=1, stop=2,
                                             orientation=3))

        f1 = aa_db.new_annotation('f1', (self.FLIM.id, 0, 12, -1))
        assert str(f1) == 'HN*K'
        assert f1.frame == -2

        f2 = aa_db.new_annotation('f2', (self.FLIM.id, 1, 10, -1))
        assert str(f2) == '*LE'
        assert f2.frame == -1

        f3 = aa_db.new_annotation('f3', (self.FLIM.id, 2, 11, -1))
        assert str(f3) == 'IIR'
        assert f3.frame == -3

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = apps_ucscensembl_test
import unittest
from testlib import testutil, PygrTestProgram

from pygr.apps.ucsc_ensembl_annot import UCSCEnsemblInterface


class UCSCEnsembl_Test(unittest.TestCase):

    def setUp(self):
        self.iface = UCSCEnsemblInterface('Bio.Seq.Genome.HUMAN.hg18')

    def test_nonexistent(self):
        'Test trying to use a genome with no Ensembl data at UCSC'
        badname = 'Nonexistent.Fake.Bogus'
        try:
            badiface = UCSCEnsemblInterface(badname)
        except KeyError:
            return
        raise ValueError("Bad sequence name %s has failed to return an error" %
                         badname)

    def test_transcriptdb(self):
        'Test interfacing with the transcript annotation database'
        trans_db = self.iface.trans_db
        mrna = trans_db['ENST00000000233']
        self.assertEqual(repr(mrna), 'annotENST00000000233[0:3295]')
        self.assertEqual(repr(mrna.sequence), 'chr7[127015694:127018989]')
        self.assertEqual(repr(mrna.mrna_sequence), 'ENST00000000233[0:1037]')

    def test_genedb(self):
        'Test interfacing with the gene annotation database'
        gene_db = self.iface.gene_db
        gene = gene_db['ENSG00000000003']
        self.assertEqual(repr(gene), 'annotENSG00000000003[0:8000]')
        self.assertEqual(repr(gene.sequence), '-chrX[99770450:99778450]')
        self.assertEqual(repr(gene_db['ENSG00000168958']),
                         'annotENSG00000168958[0:32595]')

    def test_proteindb(self):
        'Test interfacing with the protein peptide-sequence database'
        prot_db = self.iface.prot_db
        prot = prot_db['ENSP00000372525']
        self.assertEqual(repr(prot), 'ENSP00000372525')
        self.assertEqual(repr(prot.sequence), 'ENSP00000372525[0:801]')

    def test_exondb(self):
        'Test interfacing with the exon annotation database'
        exon_db = self.iface.exon_db
        exon = exon_db['ENSE00000720378']
        self.assertEqual(repr(exon), 'annotENSE00000720378[0:110]')
        self.assertEqual(repr(exon.sequence), 'chr7[127016774:127016884]')
        self.assertTrue(len(exon_db) > 200000)

    def test_snp(self):
        'Test interfacing with an SNP annotation database'
        snp130 = self.iface.get_annot_db('snp130')
        snp = snp130['rs58108140']
        self.assertEqual(snp.name, 'rs58108140')
        self.assertEqual(repr(snp.sequence), 'chr1[582:583]')
        self.assertEqual(snp.refUCSC, 'G')
        self.assertEqual(snp.observed, 'A/G')

    def test_maps(self):
        'Test mapping between different databases'
        mrna = self.iface.trans_db['ENST00000000233']
        gene = self.iface.gene_db['ENSG00000168958']
        prot = self.iface.prot_db['ENSP00000372525']
        exon = self.iface.exon_db['ENSE00000720378']
        trans_of_prot = self.iface.protein_transcript_id_map[prot]
        self.assertEqual(repr(trans_of_prot.id), "'ENST00000383052'")
        prot_of_mrna = (~self.iface.protein_transcript_id_map)[mrna]
        self.assertEqual(repr(prot_of_mrna.id), "'ENSP00000000233'")
        trans_of_gene = self.iface.transcripts_in_genes_map[gene].keys()
        self.assertEqual(repr(trans_of_gene),
                         '''[annotENST00000353339[0:32595], \
annotENST00000409565[0:32541], annotENST00000409616[0:31890], \
annotENST00000354503[0:32560], annotENST00000349901[0:32560], \
annotENST00000337110[0:32560], annotENST00000304593[0:32560], \
annotENST00000392059[0:30316], annotENST00000392058[0:28082]]''')
        gene_of_mrna = (~self.iface.transcripts_in_genes_map)[mrna].keys()
        self.assertEqual(repr(gene_of_mrna), '[annotENSG00000004059[0:3295]]')
        trans_of_exon = self.iface.ens_transcripts_of_exons_map[exon].keys()
        self.assertEqual(repr(trans_of_exon), '[annotENST00000000233[0:3295]]')
        exons_of_mrna = self.iface.ens_exons_in_transcripts_map[mrna].keys()
        self.assertEqual(repr(exons_of_mrna),
                         '''[annotENSE00001123404[0:161], \
annotENSE00000720374[0:81], annotENSE00000720378[0:110], \
annotENSE00000720381[0:72], annotENSE00000720384[0:126], \
annotENSE00000882271[0:487]]''')


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = blast_test
from itertools import *
import re
import unittest
import glob
import os
from testlib import testutil, SkipTest, PygrTestProgram
from pygr import worldbase
from pygr import sequence, cnestedlist, seqdb, blast, logger, parse_blast
from pygr.nlmsa_utils import CoordsGroupStart, CoordsGroupEnd
from pygr import translationDB


def check_results(results, correct, formatter, delta=0.01,
                  reformatCorrect=False, reformatResults=True):
    if reformatResults:
        results = reformat_results(results, formatter)

    if reformatCorrect: # reformat these data too
        correct = reformat_results(correct, formatter)
    else:
        correct.sort()

    # this is to help troubleshooting the mismatches if there are any
    mismatch = [(a, b) for a, b in zip(correct, results) if
                 testutil.approximate_cmp([a], [b], delta)]
    if mismatch:
        logger.warn('blast mismatches found')
        for m in mismatch:
            logger.warn('%s != %s' % m)

    # this is the actual test
    assert testutil.approximate_cmp(correct, results, delta) == 0


def check_results_relaxed_blastp(results, correct, formatter, delta=0.01,
                                 reformatCorrect=False, allowedLengthDiff=0,
                                 identityMin=0.6, reformatResults=True):
    if reformatResults:
        results = reformat_results(results, formatter)

    if reformatCorrect: # reformat these data too
        correct = reformat_results(correct, formatter)
    else:
        correct.sort()

    # Length of output
    assert abs(len(results) - len(correct)) <= allowedLengthDiff

    # Format check
    key_re = re.compile('^[A-Z]{3}[A-Z0-9]?_[A-Z]{2,5}$')
    for result in results:
        assert key_re.search(result[0])
        assert key_re.search(result[1])
        assert (0. < result[2] and result[2] <= 1.)

    # High-identity comparison
    results_high = []
    correct_high = []
    for result in results:
        if result[2] > identityMin:
            results_high.append(result)
    for result in correct:
        if result[2] > identityMin:
            correct_high.append(result)
    assert testutil.approximate_cmp(correct_high, results_high, delta) == 0


def check_results_relaxed_blastx(results, correct, formatter, delta=0.01,
                                 reformatCorrect=False, allowedLengthDiff=0,
                                 identityMin=0.6):
    results = reformat_results(results, formatter)

    if reformatCorrect: # reformat these data too
        correct = reformat_results(correct, formatter)
    else:
        correct.sort()

    # Length of output
    assert abs(len(results) - len(correct)) <= allowedLengthDiff

    # Format check
    for result in results:
        assert 3 * result[0] == result[2]
        assert (0. < result[3] and result[3] <= 1.)

    # High-identity comparison
    results_high = []
    correct_high = []
    for result in results:
        if result[3] > identityMin:
            results_high.append(result)
    for result in correct:
        if result[3] > identityMin:
            correct_high.append(result)
    assert testutil.approximate_cmp(correct_high, results_high, delta) == 0


def reformat_results(results, formatter):
    reffed = []
    for result in results:
        for t in result.edges(mergeMost=True):
            reffed.append(formatter(t))
    reffed.sort()
    return reffed


def pair_identity_tuple(t):
    'standard formatter for blast matches'
    return (t[0].id, t[1].id, t[2].pIdentity())


class BlastBase(unittest.TestCase):

    def setUp(self):
        hbb1_mouse = testutil.datafile('hbb1_mouse.fa')
        hbb1_mouse_rc = testutil.datafile('hbb1_mouse_rc.fa')
        sp_hbb1 = testutil.datafile('sp_hbb1')
        gapping = testutil.datafile('gapping.fa')

        self.dna = seqdb.SequenceFileDB(hbb1_mouse)
        self.dna_rc = seqdb.SequenceFileDB(hbb1_mouse_rc)
        self.prot = seqdb.SequenceFileDB(sp_hbb1)
        self.gapping = seqdb.SequenceFileDB(gapping)

    def tearDown(self):
        'do the RIGHT thing... close resources that have been opened!'
        self.dna.close()
        self.dna_rc.close()
        self.prot.close()
        self.gapping.close()


_multiblast_results = None


class Blast_Test(BlastBase):
    """
    Test basic BLAST stuff (using blastp).
    """

    def test_blastp(self):
        "Testing blastp"
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastMapping(self.prot, verbose=False)
        results = blastmap[self.prot['HBB1_XENLA']]

        check_results_relaxed_blastp([results], blastp_correct_results,
                                     pair_identity_tuple,
                                     allowedLengthDiff=2)

    def test_repr(self):
        blastmap = blast.BlastMapping(self.prot, verbose=False)
        assert '<BlastMapping' in repr(blastmap)

    def test_no_query(self):
        blastmap = blast.BlastMapping(self.dna, verbose=False)
        try:
            blastmap()
            assert 0, "should fail before this"
        except ValueError:
            pass

    def test_both_seq_and_db(self):
        "Testing db arg present"
        blastmap = blast.BlastMapping(self.prot, verbose=False)
        seq = self.prot['HBB1_XENLA']

        try:
            blastmap(seq=seq, queryDB=self.prot)
            assert 0, "should fail before this"
        except ValueError:
            pass

    def test_multiblast(self):
        "testing multi sequence blast"
        results = self.get_multiblast_results()
        check_results_relaxed_blastp(results, correct_multiblast_results,
                                     None, reformatResults=False,
                                     allowedLengthDiff=10)

    def get_multiblast_results(self):
        """return saved results or generate them if needed;
        results are saved so we only do this time-consuming operation once"""
        global _multiblast_results

        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        if not _multiblast_results:
            logger.info("running expensive multiblast")
            blastmap = blast.BlastMapping(self.prot, verbose=False)
            al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True,
                                   bidirectional=False)

            blastmap(al=al, queryDB=self.prot) # all vs all

            al.build() # construct the alignment indexes
            results = [al[seq] for seq in self.prot.values()]
            _multiblast_results = reformat_results(results,
                                                   pair_identity_tuple)

        return _multiblast_results

    def test_multiblast_single(self):
        "Test multi-sequence BLAST results, for BLASTs run one by one."
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastMapping(self.prot, verbose=False)
        al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True,
                               bidirectional=False)

        for seq in self.prot.values():
            blastmap(seq, al) # all vs all, one by one

        al.build() # construct the alignment indexes
        results = [al[seq] for seq in self.prot.values()]
        results_multi = self.get_multiblast_results()
        # Strict check must work here even on live BLAST output
        check_results(results, results_multi, pair_identity_tuple)

    def test_multiblast_long(self):
        "testing multi sequence blast with long db"
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        longerFile = testutil.datafile('sp_all_hbb')

        sp_all_hbb = seqdb.SequenceFileDB(longerFile)
        blastmap = blast.BlastMapping(self.prot, verbose=False)
        al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True,
                               bidirectional=False)
        blastmap(None, al, queryDB=sp_all_hbb) # all vs all
        al.build() # construct the alignment indexes

    def test_maskEnd(self):
        """
        This tests against a minor bug in cnestedlist where maskEnd
        is used to clip the end to the mask region.
        """
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        db = self.gapping
        blastmap = blast.BlastMapping(db)
        ungapped = db['ungapped']
        gapped = db['gapped']
        results = blastmap[gapped]

        results[ungapped]

    def test_no_bidirectional(self):
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        db = self.gapping
        gapped = db['gapped']
        ungapped = db['ungapped']

        blastmap = blast.BlastMapping(db)
        al = blastmap(queryDB=db)
        slice = al[gapped]

        found_once = False
        for src, dest, edge in al[gapped].edges():
            if src == gapped[0:40] and dest == ungapped[0:40]:
                assert not found_once, \
                       "BLAST results should not be bidirectional"
                found_once = True

        assert found_once, "should have found this match exactly once!"

    def test_formatdb_fail(self):
        db = self.gapping
        try:
            blastmap = blast.BlastMapping(db, filepath='foobarbaz.fa',
                                          blastReady=True,
                                          showFormatdbMessages=False)
            assert 0, "should not reach this point"
        except IOError:                 # should fail with 'cannot build'
            pass

        remnants = glob.glob('foobarbaz.fa.n??')
        for filename in remnants:
            os.unlink(filename)

    def test_seq_without_db(self):
        "Check that sequences without associated DBs work as query strings"
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")
        blastmap = blast.BlastMapping(self.prot, verbose=False)

        seq = self.prot['HBB1_XENLA']
        seq_no_db = sequence.Sequence(str(seq), 'HBB1_XENLA_no_db')
        slice = blastmap(seq=seq_no_db)[seq_no_db]
        assert len(slice)


class Blastx_Test(BlastBase):

    def test_blastx(self):
        "Testing blastx"
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastxMapping(self.prot, verbose=False)

        correct = [(143, 143, 429, 0.53146853146853146),
                   (143, 145, 429, 0.28275862068965518),
                   (143, 145, 429, 0.28965517241379313),
                   (143, 145, 429, 0.29655172413793102),
                   (143, 145, 429, 0.30344827586206896),
                   (144, 144, 432, 0.4513888888888889),
                   (144, 144, 432, 0.4513888888888889),
                   (145, 145, 435, 0.45517241379310347),
                   (145, 145, 435, 0.51034482758620692),
                   (146, 142, 438, 0.35616438356164382),
                   (146, 146, 438, 0.4589041095890411),
                   (146, 146, 438, 0.46575342465753422),
                   (146, 146, 438, 0.4726027397260274),
                   (146, 146, 438, 0.4726027397260274),
                   (146, 146, 438, 0.4863013698630137),
                   (146, 146, 438, 0.59589041095890416),
                   (146, 146, 438, 0.62328767123287676),
                   (146, 146, 438, 0.66438356164383561),
                   (146, 146, 438, 0.74657534246575341),
                   (146, 146, 438, 0.91095890410958902),
                   (146, 146, 438, 0.97945205479452058)]

        results = blastmap[self.dna['gi|171854975|dbj|AB364477.1|']]
        check_results_relaxed_blastx(results, correct,
                      lambda t: (len(t[0]), len(t[1]), len(t[0].sequence),
                                 t[2].pIdentity()), allowedLengthDiff=2)

    def test_blastx_rc(self):
        "Testing blastx with negative frames"
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastxMapping(self.prot, verbose=False)

        correct = [(143, 143, 429, 0.53146853146853146),
                   (143, 145, 429, 0.28275862068965518),
                   (143, 145, 429, 0.28965517241379313),
                   (143, 145, 429, 0.29655172413793102),
                   (143, 145, 429, 0.30344827586206896),
                   (144, 144, 432, 0.4513888888888889),
                   (144, 144, 432, 0.4513888888888889),
                   (145, 145, 435, 0.45517241379310347),
                   (145, 145, 435, 0.51034482758620692),
                   (146, 142, 438, 0.35616438356164382),
                   (146, 146, 438, 0.4589041095890411),
                   (146, 146, 438, 0.46575342465753422),
                   (146, 146, 438, 0.4726027397260274),
                   (146, 146, 438, 0.4726027397260274),
                   (146, 146, 438, 0.4863013698630137),
                   (146, 146, 438, 0.59589041095890416),
                   (146, 146, 438, 0.62328767123287676),
                   (146, 146, 438, 0.66438356164383561),
                   (146, 146, 438, 0.74657534246575341),
                   (146, 146, 438, 0.91095890410958902),
                   (146, 146, 438, 0.97945205479452058)]

        results = blastmap[self.dna_rc['hbb1_mouse_RC']]
        check_results_relaxed_blastx(results, correct,
                      lambda t: (len(t[0]), len(t[1]), len(t[0].sequence),
                                 t[2].pIdentity()), allowedLengthDiff=2)

        results = blastmap[self.dna_rc['hbb1_mouse_RC_2']]
        check_results_relaxed_blastx(results, correct,
                      lambda t: (len(t[0]), len(t[1]), len(t[0].sequence),
                                 t[2].pIdentity()), allowedLengthDiff=2)

        results = blastmap[self.dna_rc['hbb1_mouse_RC_3']]
        check_results_relaxed_blastx(results, correct,
                      lambda t: (len(t[0]), len(t[1]), len(t[0].sequence),
                                 t[2].pIdentity()), allowedLengthDiff=2)

    def test_repr(self):
        blastmap = blast.BlastxMapping(self.prot, verbose=False)
        assert '<BlastxMapping' in repr(blastmap)

    def test_blastx_no_blastp(self):
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastxMapping(self.prot, verbose=False)

        try:
            results = blastmap(self.prot['HBB1_MOUSE'])
            raise AssertionError('failed to trap blastp in BlastxMapping')
        except ValueError:
            pass

    def test_no_query(self):
        blastmap = blast.BlastxMapping(self.prot, verbose=False)
        try:
            blastmap()
            assert 0, "should fail before this"
        except ValueError:
            pass

    def test_both_seq_and_db(self):
        "Testing blastp"
        blastmap = blast.BlastxMapping(self.prot, verbose=False)
        seq = self.prot['HBB1_XENLA']

        try:
            blastmap(seq=seq, queryDB=self.prot)
            assert 0, "should fail before this"
        except ValueError:
            pass

    def test_translation_db_in_results_of_db_search(self):
        """
        Test that the NLMSA in a BlastxMapping properly picks up the
        translationDB from the query sequence dict.
        """
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")
        blastmap = blast.BlastxMapping(self.prot, verbose=False)
        results = blastmap(queryDB=self.dna)

        tdb = translationDB.get_translation_db(self.dna)
        assert tdb.annodb in results.seqDict.dicts

    def test_translation_db_in_results_of_seq_search(self):
        """
        Test that the NLMSA in a BlastxMapping properly picks up the
        translationDB from a single input sequence.
        """
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")
        blastmap = blast.BlastxMapping(self.prot, verbose=False)

        query_seq = self.dna['gi|171854975|dbj|AB364477.1|']
        results = blastmap(seq=query_seq)

        tdb = translationDB.get_translation_db(self.dna)
        assert tdb.annodb in results.seqDict.dicts

    def test_translated_seqs_in_results(self):
        """
        Only NLMSASlices for the query sequence should show up in
        BlastxMapping.__getitem__, right?
        """
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")
        blastmap = blast.BlastxMapping(self.prot, verbose=False)

        query_seq = self.dna['gi|171854975|dbj|AB364477.1|']
        results = blastmap[query_seq]

        tdb = translationDB.get_translation_db(self.dna)
        annodb = tdb.annodb

        for slice in results:
            assert slice.seq.id in annodb, '%s not in annodb!' % slice.seq.id

    def test_non_consumable_results(self):
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")
        blastmap = blast.BlastxMapping(self.prot, verbose=False)

        query_seq = self.dna['gi|171854975|dbj|AB364477.1|']
        results = blastmap[query_seq]

        x = list(results)
        y = list(results)

        assert len(x), x
        assert x == y, "BlastxMapping.__getitem__ should return list"


class Tblastn_Test(BlastBase):

    def test_tblastn(self):
        "tblastn test"
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastMapping(self.dna, verbose=False)
        correct = [(144, 144, 432, 0.451)]

        result = blastmap[self.prot['HBB1_XENLA']]
        check_results_relaxed_blastx([result], correct,
                      lambda t: (len(t[1]), len(t[0]), len(t[1].sequence),
                                 t[2].pIdentity()))

    def test_tblastn_no_blastx(self):
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastMapping(self.prot)
        try:
            results = blastmap[self.dna['gi|171854975|dbj|AB364477.1|']]
            raise AssertionError('failed to trap blastx in BlastMapping')
        except ValueError:
            pass

    def test_megablast(self):
        '''test megablast'''
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.MegablastMapping(self.dna, verbose=False)
        # must use copy of sequence to get "self matches" from NLMSA...
        query = seqdb.Sequence(str(self.dna['gi|171854975|dbj|AB364477.1|']),
                               'foo')
        try:
            result = blastmap[query]
        except OSError: # silently ignore missing RepeatMasker, megablast
            return
        found = [(len(t[0]), len(t[1])) for t in result.edges()]
        assert found == [(444, 444)]

    def test_megablast_repr(self):
        blastmap = blast.MegablastMapping(self.dna, verbose=False)
        assert '<MegablastMapping' in repr(blastmap)

    def test_bad_subject(self):
        "Test bad subjects"

        correctCoords = ((12, 63, 99508, 99661),
                         (65, 96, 99661, 99754),
                         (96, 108, 99778, 99814),
                         (108, 181, 99826, 100045))

        fp = file(testutil.datafile('bad_tblastn.txt'))
        try:
            p = parse_blast.BlastHitParser()
            it = iter(correctCoords)
            for ival in p.parse_file(fp):
                if not isinstance(ival, (CoordsGroupStart, CoordsGroupEnd)):
                    assert (ival.src_start, ival.src_end,
                            ival.dest_start, ival.dest_end) \
                        == it.next()
        finally:
            fp.close()


class BlastParsers_Test(BlastBase):

    def test_blastp_parser(self):
        "Testing blastp parser"
        blastp_output = open(testutil.datafile('blastp_output.txt'), 'r')

        seq_dict = {'HBB1_XENLA': self.prot['HBB1_XENLA']}
        prot_index = blast.BlastIDIndex(self.prot)
        try:
            alignment = blast.read_blast_alignment(blastp_output, seq_dict,
                                                   prot_index)
            results = alignment[self.prot['HBB1_XENLA']]
        finally:
            blastp_output.close()

        check_results([results], blastp_correct_results, pair_identity_tuple)

    def test_multiblast_parser(self):
        "Testing multiblast parser"
        multiblast_output = open(testutil.datafile('multiblast_output.txt'),
                                 'r')

        try:
            al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True,
                                   bidirectional=False)
            al = blast.read_blast_alignment(multiblast_output, self.prot,
                                            blast.BlastIDIndex(self.prot), al)
        finally:
            multiblast_output.close()
        al.build()
        results = [al[seq] for seq in self.prot.values()]

        check_results(results, correct_multiblast_results,
                      pair_identity_tuple)

    def test_multiblast_parser_long(self):
        "Testing multiblast parser with long input"
        longerFile = testutil.datafile('sp_all_hbb')
        sp_all_hbb = seqdb.SequenceFileDB(longerFile)

        filename = testutil.datafile('multiblast_long_output.txt')
        multiblast_output = open(filename, 'r')
        try:
            al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True,
                                   bidirectional=False)
            al = blast.read_blast_alignment(multiblast_output, sp_all_hbb,
                                            self.prot, al)
        finally:
            multiblast_output.close()
        al.build()

        results = []
        for seq in sp_all_hbb.values():
            try:
                results.append(al[seq])
            except KeyError:
                pass
        correctfile = file(testutil.datafile('multiblast_long_correct.txt'),
                           'r')
        try:
            correct = []
            for line in correctfile:
                t = line.split()
                correct.append((t[0], t[1], float(t[2])))
        finally:
            correctfile.close()
        check_results(results, correct, pair_identity_tuple)

    def test_blastx_parser(self):
        "Testing blastx parser"
        blastx_output = open(testutil.datafile('blastx_output.txt'), 'r')
        seq_dict = {'gi|171854975|dbj|AB364477.1|':
                    self.dna['gi|171854975|dbj|AB364477.1|']}
        try:
            results = blast.read_blast_alignment(blastx_output,
                                                 seq_dict,
                                                 blast.BlastIDIndex(self.prot),
                                                 translateSrc=True)
        finally:
            blastx_output.close()
        correct = [(143, 143, 429, 0.53146853146853146),
                   (143, 145, 429, 0.28275862068965518),
                   (143, 145, 429, 0.28965517241379313),
                   (143, 145, 429, 0.29655172413793102),
                   (143, 145, 429, 0.30344827586206896),
                   (144, 144, 432, 0.4513888888888889),
                   (144, 144, 432, 0.4513888888888889),
                   (145, 145, 435, 0.45517241379310347),
                   (145, 145, 435, 0.51034482758620692),
                   (146, 142, 438, 0.35616438356164382),
                   (146, 146, 438, 0.4589041095890411),
                   (146, 146, 438, 0.46575342465753422),
                   (146, 146, 438, 0.4726027397260274),
                   (146, 146, 438, 0.4726027397260274),
                   (146, 146, 438, 0.4863013698630137),
                   (146, 146, 438, 0.59589041095890416),
                   (146, 146, 438, 0.62328767123287676),
                   (146, 146, 438, 0.66438356164383561),
                   (146, 146, 438, 0.74657534246575341),
                   (146, 146, 438, 0.91095890410958902),
                   (146, 146, 438, 0.97945205479452058)]

        check_results([results], correct,
                      lambda t: (len(t[0]), len(t[1]), len(t[0].sequence),
                                 t[2].pIdentity()))

    def test_tblastn_parser(self):
        "Testing tblastn parser"
        seq_dict = {'HBB1_XENLA': self.prot['HBB1_XENLA']}
        dna_db = blast.BlastIDIndex(self.dna)
        tblastn_output = open(testutil.datafile('tblastn_output.txt'), 'r')
        try:
            al = blast.read_blast_alignment(tblastn_output, seq_dict,
                                            dna_db, translateDest=True)
            result = al[self.prot['HBB1_XENLA']]
        finally:
            tblastn_output.close()
        src, dest, edge = iter(result.edges()).next()

        self.assertEqual(str(src),
            'LTAHDRQLINSTWGKLCAKTIGQEALGRLLWTYPWTQRYFSSFGNLNSADAVFHNEAVAAHGEK'
            'VVTSIGEAIKHMDDIKGYYAQLSKYHSETLHVDPLNFKRFGGCLSIALARHFHEEYTPELHAAY'
            'EHLFDAIADALGKGYH')
        self.assertEqual(str(dest),
            'LTDAEKAAVSGLWGKVNSDEVGGEALGRLLVVYPWTQRYFDSFGDLSSASAIMGNAKVKAHGKK'
            'VITAFNEGLNHLDSLKGTFASLSELHCDKLHVDPENFRLLGNMIVIVLGHHLGKDFTPAAQAAF'
            'QKVMAGVATALAHKYH')
        self.assertEqual(str(dest.sequence),
            'CTGACTGATGCTGAGAAGGCTGCTGTCTCTGGCCTGTGGGGAAAGGTGAACTCCGATGAAGTTG'
            'GTGGTGAGGCCCTGGGCAGGCTGCTGGTTGTCTACCCTTGGACCCAGAGGTACTTTGATAGCTT'
            'TGGAGACCTATCCTCTGCCTCTGCTATCATGGGTAATGCCAAAGTGAAGGCCCATGGCAAGAAA'
            'GTGATAACTGCCTTTAACGAGGGCCTGAATCACTTGGACAGCCTCAAGGGCACCTTTGCCAGCC'
            'TCAGTGAGCTCCACTGTGACAAGCTCCATGTGGATCCTGAGAACTTCAGGCTCCTGGGCAATAT'
            'GATCGTGATTGTGCTGGGCCACCACCTGGGCAAGGATTTCACCCCCGCTGCACAGGCTGCCTTC'
            'CAGAAGGTGATGGCTGGAGTGGCCACTGCCCTGGCTCACAAGTACCAC')

        self.assertAlmostEqual(edge.pIdentity(), 0.451, 3)


# not used currently
def all_vs_all_blast_save():
    """
    Creates the blast files used during testing.
    Must be called before running the tests
    """

    tempdir = testutil.TempDir('blast-test')
    testutil.change_pygrdatapath(tempdir.path)

    sp_hbb1 = testutil.datafile('sp_hbb1')
    all_vs_all = testutil.tempdatafile('all_vs_all')

    sp = seqdb.BlastDB(sp_hbb1)
    msa = cnestedlist.NLMSA(all_vs_all, mode='w', pairwiseMode=True,
                            bidirectional=False)

    # get strong homologs, save alignment in msa for every sequence
    reader = islice(sp.iteritems(), None)
    for id, s in reader:
        sp.blast(s, msa, expmax=1e-10, verbose=False)

    # done constructing the alignment, so build the alignment db indexes
    msa.build(saveSeqDict=True)

    db = msa.seqDict.dicts.keys()[0]
    working, result = {}, {}
    for k in db.values():
        edges = msa[k].edges(minAlignSize=12, pIdentityMin=0.5)
        for t in edges:
            assert len(t[0]) >= 12
        tmpdict = dict(map(lambda x: (x, None),
                           [(str(t[0]), str(t[1]),
                             t[2].pIdentity(trapOverflow=False)) for t in
                            edges]))
        result[repr(k)] = tmpdict.keys()
        result[repr(k)].sort()

    # save it into worldbase
    data = testutil.TestData()
    data.__doc__ = 'sp_allvall'
    data.result = result
    worldbase.Bio.Blast = data
    worldbase.commit()

    #return msa

###

blastp_correct_results = \
        [('HBB1_XENLA', 'HBB0_PAGBO', 0.44055944055944057),
         ('HBB1_XENLA', 'HBB1_ANAMI', 0.45323741007194246),
         ('HBB1_XENLA', 'HBB1_CYGMA', 0.46715328467153283),
         ('HBB1_XENLA', 'HBB1_IGUIG', 0.48951048951048953),
         ('HBB1_XENLA', 'HBB1_MOUSE', 0.44444444444444442),
         ('HBB1_XENLA', 'HBB1_ONCMY', 0.39436619718309857),
         ('HBB1_XENLA', 'HBB1_PAGBO', 0.44055944055944057),
         ('HBB1_XENLA', 'HBB1_RAT', 0.45833333333333331),
         ('HBB1_XENLA', 'HBB1_SPHPU', 0.4825174825174825),
         ('HBB1_XENLA', 'HBB1_TAPTE', 0.47222222222222221),
         ('HBB1_XENLA', 'HBB1_TORMA', 0.33793103448275863),
         ('HBB1_XENLA', 'HBB1_TRICR', 0.49305555555555558),
         ('HBB1_XENLA', 'HBB1_UROHA', 0.3776223776223776),
         ('HBB1_XENLA', 'HBB1_VAREX', 0.5174825174825175),
         ('HBB1_XENLA', 'HBB1_XENBO', 0.96551724137931039),
         ('HBB1_XENLA', 'HBB1_XENLA', 1.0),
         ('HBB1_XENLA', 'HBB1_XENTR', 0.75),
         ('HBB1_XENLA', 'MYG_DIDMA', 0.32075471698113206),
         ('HBB1_XENLA', 'MYG_ELEMA', 0.26415094339622641),
         ('HBB1_XENLA', 'MYG_ERIEU', 0.32075471698113206),
         ('HBB1_XENLA', 'MYG_ESCGI', 0.28282828282828282),
         ('HBB1_XENLA', 'MYG_GALCR', 0.32075471698113206)]


correct_multiblast_results = \
        [('HBB0_PAGBO', 'HBB0_PAGBO', 1.0),
         ('HBB0_PAGBO', 'HBB1_ANAMI', 0.66896551724137931),
         ('HBB0_PAGBO', 'HBB1_CYGMA', 0.68493150684931503),
         ('HBB0_PAGBO', 'HBB1_IGUIG', 0.4863013698630137),
         ('HBB0_PAGBO', 'HBB1_MOUSE', 0.45205479452054792),
         ('HBB0_PAGBO', 'HBB1_ONCMY', 0.55172413793103448),
         ('HBB0_PAGBO', 'HBB1_PAGBO', 0.69178082191780821),
         ('HBB0_PAGBO', 'HBB1_RAT', 0.4589041095890411),
         ('HBB0_PAGBO', 'HBB1_SPHPU', 0.4589041095890411),
         ('HBB0_PAGBO', 'HBB1_TAPTE', 0.4863013698630137),
         ('HBB0_PAGBO', 'HBB1_TORMA', 0.31506849315068491),
         ('HBB0_PAGBO', 'HBB1_TRICR', 0.4375),
         ('HBB0_PAGBO', 'HBB1_UROHA', 0.4041095890410959),
         ('HBB0_PAGBO', 'HBB1_VAREX', 0.49315068493150682),
         ('HBB0_PAGBO', 'HBB1_XENBO', 0.43356643356643354),
         ('HBB0_PAGBO', 'HBB1_XENLA', 0.44055944055944057),
         ('HBB0_PAGBO', 'HBB1_XENTR', 0.4726027397260274),
         ('HBB0_PAGBO', 'MYG_DIDMA', 0.22222222222222221),
         ('HBB0_PAGBO', 'MYG_ELEMA', 0.20833333333333334),
         ('HBB0_PAGBO', 'MYG_ERIEU', 0.21527777777777779),
         ('HBB0_PAGBO', 'MYG_ESCGI', 0.25),
         ('HBB0_PAGBO', 'MYG_GALCR', 0.24305555555555555),
         ('HBB1_ANAMI', 'HBB0_PAGBO', 0.66896551724137931),
         ('HBB1_ANAMI', 'HBB1_ANAMI', 1.0),
         ('HBB1_ANAMI', 'HBB1_CYGMA', 0.75862068965517238),
         ('HBB1_ANAMI', 'HBB1_IGUIG', 0.47586206896551725),
         ('HBB1_ANAMI', 'HBB1_MOUSE', 0.45517241379310347),
         ('HBB1_ANAMI', 'HBB1_ONCMY', 0.59310344827586203),
         ('HBB1_ANAMI', 'HBB1_PAGBO', 0.75862068965517238),
         ('HBB1_ANAMI', 'HBB1_RAT', 0.48965517241379308),
         ('HBB1_ANAMI', 'HBB1_SPHPU', 0.46206896551724136),
         ('HBB1_ANAMI', 'HBB1_TAPTE', 0.48965517241379308),
         ('HBB1_ANAMI', 'HBB1_TORMA', 0.32413793103448274),
         ('HBB1_ANAMI', 'HBB1_TRICR', 0.41258741258741261),
         ('HBB1_ANAMI', 'HBB1_UROHA', 0.38620689655172413),
         ('HBB1_ANAMI', 'HBB1_VAREX', 0.48275862068965519),
         ('HBB1_ANAMI', 'HBB1_XENBO', 0.4460431654676259),
         ('HBB1_ANAMI', 'HBB1_XENLA', 0.45323741007194246),
         ('HBB1_ANAMI', 'HBB1_XENTR', 0.4689655172413793),
         ('HBB1_CYGMA', 'HBB0_PAGBO', 0.68493150684931503),
         ('HBB1_CYGMA', 'HBB1_ANAMI', 0.75862068965517238),
         ('HBB1_CYGMA', 'HBB1_CYGMA', 1.0),
         ('HBB1_CYGMA', 'HBB1_IGUIG', 0.5),
         ('HBB1_CYGMA', 'HBB1_MOUSE', 0.47945205479452052),
         ('HBB1_CYGMA', 'HBB1_ONCMY', 0.53103448275862064),
         ('HBB1_CYGMA', 'HBB1_PAGBO', 0.86986301369863017),
         ('HBB1_CYGMA', 'HBB1_RAT', 0.50684931506849318),
         ('HBB1_CYGMA', 'HBB1_SPHPU', 0.47945205479452052),
         ('HBB1_CYGMA', 'HBB1_TAPTE', 0.4726027397260274),
         ('HBB1_CYGMA', 'HBB1_TORMA', 0.33561643835616439),
         ('HBB1_CYGMA', 'HBB1_TRICR', 0.4375),
         ('HBB1_CYGMA', 'HBB1_UROHA', 0.36986301369863012),
         ('HBB1_CYGMA', 'HBB1_VAREX', 0.4863013698630137),
         ('HBB1_CYGMA', 'HBB1_XENBO', 0.45985401459854014),
         ('HBB1_CYGMA', 'HBB1_XENLA', 0.46715328467153283),
         ('HBB1_CYGMA', 'HBB1_XENTR', 0.47945205479452052),
         ('HBB1_CYGMA', 'MYG_ESCGI', 0.2361111111111111),
         ('HBB1_IGUIG', 'HBB0_PAGBO', 0.4863013698630137),
         ('HBB1_IGUIG', 'HBB1_ANAMI', 0.47586206896551725),
         ('HBB1_IGUIG', 'HBB1_CYGMA', 0.5),
         ('HBB1_IGUIG', 'HBB1_IGUIG', 1.0),
         ('HBB1_IGUIG', 'HBB1_MOUSE', 0.63013698630136983),
         ('HBB1_IGUIG', 'HBB1_ONCMY', 0.51034482758620692),
         ('HBB1_IGUIG', 'HBB1_PAGBO', 0.4863013698630137),
         ('HBB1_IGUIG', 'HBB1_RAT', 0.61643835616438358),
         ('HBB1_IGUIG', 'HBB1_SPHPU', 0.71232876712328763),
         ('HBB1_IGUIG', 'HBB1_TAPTE', 0.64383561643835618),
         ('HBB1_IGUIG', 'HBB1_TORMA', 0.36301369863013699),
         ('HBB1_IGUIG', 'HBB1_TRICR', 0.47916666666666669),
         ('HBB1_IGUIG', 'HBB1_UROHA', 0.64383561643835618),
         ('HBB1_IGUIG', 'HBB1_VAREX', 0.77397260273972601),
         ('HBB1_IGUIG', 'HBB1_XENBO', 0.4825174825174825),
         ('HBB1_IGUIG', 'HBB1_XENLA', 0.48951048951048953),
         ('HBB1_IGUIG', 'HBB1_XENTR', 0.49315068493150682),
         ('HBB1_IGUIG', 'MYG_DIDMA', 0.25179856115107913),
         ('HBB1_IGUIG', 'MYG_ERIEU', 0.28368794326241137),
         ('HBB1_IGUIG', 'MYG_ESCGI', 0.27659574468085107),
         ('HBB1_IGUIG', 'MYG_GALCR', 0.28368794326241137),
         ('HBB1_MOUSE', 'HBB0_PAGBO', 0.45205479452054792),
         ('HBB1_MOUSE', 'HBB1_ANAMI', 0.45517241379310347),
         ('HBB1_MOUSE', 'HBB1_CYGMA', 0.47945205479452052),
         ('HBB1_MOUSE', 'HBB1_IGUIG', 0.63013698630136983),
         ('HBB1_MOUSE', 'HBB1_MOUSE', 1.0),
         ('HBB1_MOUSE', 'HBB1_ONCMY', 0.50344827586206897),
         ('HBB1_MOUSE', 'HBB1_PAGBO', 0.4726027397260274),
         ('HBB1_MOUSE', 'HBB1_RAT', 0.9178082191780822),
         ('HBB1_MOUSE', 'HBB1_SPHPU', 0.65753424657534243),
         ('HBB1_MOUSE', 'HBB1_TAPTE', 0.76027397260273977),
         ('HBB1_MOUSE', 'HBB1_TORMA', 0.35616438356164382),
         ('HBB1_MOUSE', 'HBB1_TRICR', 0.52083333333333337),
         ('HBB1_MOUSE', 'HBB1_UROHA', 0.47945205479452052),
         ('HBB1_MOUSE', 'HBB1_VAREX', 0.6095890410958904),
         ('HBB1_MOUSE', 'HBB1_XENBO', 0.44444444444444442),
         ('HBB1_MOUSE', 'HBB1_XENLA', 0.44444444444444442),
         ('HBB1_MOUSE', 'HBB1_XENTR', 0.4589041095890411),
         ('HBB1_MOUSE', 'MYG_DIDMA', 0.29655172413793102),
         ('HBB1_MOUSE', 'MYG_ELEMA', 0.27586206896551724),
         ('HBB1_MOUSE', 'MYG_ERIEU', 0.30344827586206896),
         ('HBB1_MOUSE', 'MYG_ESCGI', 0.28965517241379313),
         ('HBB1_MOUSE', 'MYG_GALCR', 0.28275862068965518),
         ('HBB1_ONCMY', 'HBB0_PAGBO', 0.55172413793103448),
         ('HBB1_ONCMY', 'HBB1_ANAMI', 0.59310344827586203),
         ('HBB1_ONCMY', 'HBB1_CYGMA', 0.53103448275862064),
         ('HBB1_ONCMY', 'HBB1_IGUIG', 0.51034482758620692),
         ('HBB1_ONCMY', 'HBB1_MOUSE', 0.50344827586206897),
         ('HBB1_ONCMY', 'HBB1_ONCMY', 1.0),
         ('HBB1_ONCMY', 'HBB1_PAGBO', 0.56551724137931036),
         ('HBB1_ONCMY', 'HBB1_RAT', 0.50344827586206897),
         ('HBB1_ONCMY', 'HBB1_SPHPU', 0.46206896551724136),
         ('HBB1_ONCMY', 'HBB1_TAPTE', 0.50344827586206897),
         ('HBB1_ONCMY', 'HBB1_TORMA', 0.33793103448275863),
         ('HBB1_ONCMY', 'HBB1_TRICR', 0.41258741258741261),
         ('HBB1_ONCMY', 'HBB1_UROHA', 0.44827586206896552),
         ('HBB1_ONCMY', 'HBB1_VAREX', 0.48965517241379308),
         ('HBB1_ONCMY', 'HBB1_XENBO', 0.40140845070422537),
         ('HBB1_ONCMY', 'HBB1_XENLA', 0.39436619718309857),
         ('HBB1_ONCMY', 'HBB1_XENTR', 0.39310344827586208),
         ('HBB1_ONCMY', 'MYG_DIDMA', 0.25694444444444442),
         ('HBB1_ONCMY', 'MYG_ERIEU', 0.2361111111111111),
         ('HBB1_ONCMY', 'MYG_ESCGI', 0.25),
         ('HBB1_ONCMY', 'MYG_GALCR', 0.24305555555555555),
         ('HBB1_PAGBO', 'HBB0_PAGBO', 0.69178082191780821),
         ('HBB1_PAGBO', 'HBB1_ANAMI', 0.75862068965517238),
         ('HBB1_PAGBO', 'HBB1_CYGMA', 0.86986301369863017),
         ('HBB1_PAGBO', 'HBB1_IGUIG', 0.4863013698630137),
         ('HBB1_PAGBO', 'HBB1_MOUSE', 0.4726027397260274),
         ('HBB1_PAGBO', 'HBB1_ONCMY', 0.56551724137931036),
         ('HBB1_PAGBO', 'HBB1_PAGBO', 1.0),
         ('HBB1_PAGBO', 'HBB1_RAT', 0.4863013698630137),
         ('HBB1_PAGBO', 'HBB1_SPHPU', 0.4726027397260274),
         ('HBB1_PAGBO', 'HBB1_TAPTE', 0.46575342465753422),
         ('HBB1_PAGBO', 'HBB1_TORMA', 0.34931506849315069),
         ('HBB1_PAGBO', 'HBB1_TRICR', 0.4375),
         ('HBB1_PAGBO', 'HBB1_UROHA', 0.35616438356164382),
         ('HBB1_PAGBO', 'HBB1_VAREX', 0.4726027397260274),
         ('HBB1_PAGBO', 'HBB1_XENBO', 0.43356643356643354),
         ('HBB1_PAGBO', 'HBB1_XENLA', 0.44055944055944057),
         ('HBB1_PAGBO', 'HBB1_XENTR', 0.47945205479452052),
         ('HBB1_RAT', 'HBB0_PAGBO', 0.4589041095890411),
         ('HBB1_RAT', 'HBB1_ANAMI', 0.48965517241379308),
         ('HBB1_RAT', 'HBB1_CYGMA', 0.50684931506849318),
         ('HBB1_RAT', 'HBB1_IGUIG', 0.61643835616438358),
         ('HBB1_RAT', 'HBB1_MOUSE', 0.9178082191780822),
         ('HBB1_RAT', 'HBB1_ONCMY', 0.50344827586206897),
         ('HBB1_RAT', 'HBB1_PAGBO', 0.4863013698630137),
         ('HBB1_RAT', 'HBB1_RAT', 1.0),
         ('HBB1_RAT', 'HBB1_SPHPU', 0.66438356164383561),
         ('HBB1_RAT', 'HBB1_TAPTE', 0.76712328767123283),
         ('HBB1_RAT', 'HBB1_TORMA', 0.35616438356164382),
         ('HBB1_RAT', 'HBB1_TRICR', 0.52777777777777779),
         ('HBB1_RAT', 'HBB1_UROHA', 0.5),
         ('HBB1_RAT', 'HBB1_VAREX', 0.62328767123287676),
         ('HBB1_RAT', 'HBB1_XENBO', 0.45833333333333331),
         ('HBB1_RAT', 'HBB1_XENLA', 0.45833333333333331),
         ('HBB1_RAT', 'HBB1_XENTR', 0.45205479452054792),
         ('HBB1_RAT', 'MYG_DIDMA', 0.29655172413793102),
         ('HBB1_RAT', 'MYG_ELEMA', 0.28275862068965518),
         ('HBB1_RAT', 'MYG_ERIEU', 0.29655172413793102),
         ('HBB1_RAT', 'MYG_ESCGI', 0.28275862068965518),
         ('HBB1_RAT', 'MYG_GALCR', 0.27586206896551724),
         ('HBB1_SPHPU', 'HBB0_PAGBO', 0.4589041095890411),
         ('HBB1_SPHPU', 'HBB1_ANAMI', 0.46206896551724136),
         ('HBB1_SPHPU', 'HBB1_CYGMA', 0.47945205479452052),
         ('HBB1_SPHPU', 'HBB1_IGUIG', 0.71232876712328763),
         ('HBB1_SPHPU', 'HBB1_MOUSE', 0.65753424657534243),
         ('HBB1_SPHPU', 'HBB1_ONCMY', 0.46206896551724136),
         ('HBB1_SPHPU', 'HBB1_PAGBO', 0.4726027397260274),
         ('HBB1_SPHPU', 'HBB1_RAT', 0.66438356164383561),
         ('HBB1_SPHPU', 'HBB1_SPHPU', 1.0),
         ('HBB1_SPHPU', 'HBB1_TAPTE', 0.63698630136986301),
         ('HBB1_SPHPU', 'HBB1_TORMA', 0.38356164383561642),
         ('HBB1_SPHPU', 'HBB1_TRICR', 0.47916666666666669),
         ('HBB1_SPHPU', 'HBB1_UROHA', 0.54109589041095896),
         ('HBB1_SPHPU', 'HBB1_VAREX', 0.69178082191780821),
         ('HBB1_SPHPU', 'HBB1_XENBO', 0.48951048951048953),
         ('HBB1_SPHPU', 'HBB1_XENLA', 0.4825174825174825),
         ('HBB1_SPHPU', 'HBB1_XENTR', 0.4726027397260274),
         ('HBB1_TAPTE', 'HBB0_PAGBO', 0.4863013698630137),
         ('HBB1_TAPTE', 'HBB1_ANAMI', 0.48965517241379308),
         ('HBB1_TAPTE', 'HBB1_CYGMA', 0.4726027397260274),
         ('HBB1_TAPTE', 'HBB1_IGUIG', 0.64383561643835618),
         ('HBB1_TAPTE', 'HBB1_MOUSE', 0.76027397260273977),
         ('HBB1_TAPTE', 'HBB1_ONCMY', 0.50344827586206897),
         ('HBB1_TAPTE', 'HBB1_PAGBO', 0.46575342465753422),
         ('HBB1_TAPTE', 'HBB1_RAT', 0.76712328767123283),
         ('HBB1_TAPTE', 'HBB1_SPHPU', 0.63698630136986301),
         ('HBB1_TAPTE', 'HBB1_TAPTE', 1.0),
         ('HBB1_TAPTE', 'HBB1_TORMA', 0.34931506849315069),
         ('HBB1_TAPTE', 'HBB1_TRICR', 0.4861111111111111),
         ('HBB1_TAPTE', 'HBB1_UROHA', 0.51369863013698636),
         ('HBB1_TAPTE', 'HBB1_VAREX', 0.62328767123287676),
         ('HBB1_TAPTE', 'HBB1_XENBO', 0.4861111111111111),
         ('HBB1_TAPTE', 'HBB1_XENLA', 0.47222222222222221),
         ('HBB1_TAPTE', 'HBB1_XENTR', 0.45205479452054792),
         ('HBB1_TAPTE', 'MYG_DIDMA', 0.26277372262773724),
         ('HBB1_TAPTE', 'MYG_ERIEU', 0.27007299270072993),
         ('HBB1_TAPTE', 'MYG_ESCGI', 0.30344827586206896),
         ('HBB1_TAPTE', 'MYG_GALCR', 0.27007299270072993),
         ('HBB1_TORMA', 'HBB0_PAGBO', 0.31506849315068491),
         ('HBB1_TORMA', 'HBB1_ANAMI', 0.32413793103448274),
         ('HBB1_TORMA', 'HBB1_CYGMA', 0.33561643835616439),
         ('HBB1_TORMA', 'HBB1_IGUIG', 0.36301369863013699),
         ('HBB1_TORMA', 'HBB1_MOUSE', 0.35616438356164382),
         ('HBB1_TORMA', 'HBB1_ONCMY', 0.33793103448275863),
         ('HBB1_TORMA', 'HBB1_PAGBO', 0.34931506849315069),
         ('HBB1_TORMA', 'HBB1_RAT', 0.35616438356164382),
         ('HBB1_TORMA', 'HBB1_SPHPU', 0.38356164383561642),
         ('HBB1_TORMA', 'HBB1_TAPTE', 0.34931506849315069),
         ('HBB1_TORMA', 'HBB1_TORMA', 1.0),
         ('HBB1_TORMA', 'HBB1_TRICR', 0.31724137931034485),
         ('HBB1_TORMA', 'HBB1_UROHA', 0.29452054794520549),
         ('HBB1_TORMA', 'HBB1_VAREX', 0.35616438356164382),
         ('HBB1_TORMA', 'HBB1_XENBO', 0.34482758620689657),
         ('HBB1_TORMA', 'HBB1_XENLA', 0.33793103448275863),
         ('HBB1_TORMA', 'HBB1_XENTR', 0.33561643835616439),
         ('HBB1_TORMA', 'MYG_ESCGI', 0.25675675675675674),
         ('HBB1_TRICR', 'HBB0_PAGBO', 0.4375),
         ('HBB1_TRICR', 'HBB1_ANAMI', 0.41258741258741261),
         ('HBB1_TRICR', 'HBB1_CYGMA', 0.4375),
         ('HBB1_TRICR', 'HBB1_IGUIG', 0.47916666666666669),
         ('HBB1_TRICR', 'HBB1_MOUSE', 0.52083333333333337),
         ('HBB1_TRICR', 'HBB1_ONCMY', 0.41258741258741261),
         ('HBB1_TRICR', 'HBB1_PAGBO', 0.4375),
         ('HBB1_TRICR', 'HBB1_RAT', 0.52777777777777779),
         ('HBB1_TRICR', 'HBB1_SPHPU', 0.47916666666666669),
         ('HBB1_TRICR', 'HBB1_TAPTE', 0.4861111111111111),
         ('HBB1_TRICR', 'HBB1_TORMA', 0.31724137931034485),
         ('HBB1_TRICR', 'HBB1_TRICR', 1.0),
         ('HBB1_TRICR', 'HBB1_UROHA', 0.3611111111111111),
         ('HBB1_TRICR', 'HBB1_VAREX', 0.4513888888888889),
         ('HBB1_TRICR', 'HBB1_XENBO', 0.4861111111111111),
         ('HBB1_TRICR', 'HBB1_XENLA', 0.49305555555555558),
         ('HBB1_TRICR', 'HBB1_XENTR', 0.49305555555555558),
         ('HBB1_UROHA', 'HBB0_PAGBO', 0.4041095890410959),
         ('HBB1_UROHA', 'HBB1_ANAMI', 0.42857142857142855),
         ('HBB1_UROHA', 'HBB1_CYGMA', 0.36986301369863012),
         ('HBB1_UROHA', 'HBB1_IGUIG', 0.64383561643835618),
         ('HBB1_UROHA', 'HBB1_MOUSE', 0.51666666666666672),
         ('HBB1_UROHA', 'HBB1_ONCMY', 0.50420168067226889),
         ('HBB1_UROHA', 'HBB1_PAGBO', 0.38333333333333336),
         ('HBB1_UROHA', 'HBB1_RAT', 0.54166666666666663),
         ('HBB1_UROHA', 'HBB1_SPHPU', 0.54109589041095896),
         ('HBB1_UROHA', 'HBB1_TAPTE', 0.55833333333333335),
         ('HBB1_UROHA', 'HBB1_TORMA', 0.31034482758620691),
         ('HBB1_UROHA', 'HBB1_TRICR', 0.39316239316239315),
         ('HBB1_UROHA', 'HBB1_UROHA', 1.0),
         ('HBB1_UROHA', 'HBB1_VAREX', 0.59589041095890416),
         ('HBB1_UROHA', 'HBB1_XENBO', 0.42608695652173911),
         ('HBB1_UROHA', 'HBB1_XENLA', 0.41739130434782606),
         ('HBB1_UROHA', 'HBB1_XENTR', 0.40000000000000002),
         ('HBB1_UROHA', 'MYG_ERIEU', 0.27927927927927926),
         ('HBB1_VAREX', 'HBB0_PAGBO', 0.49315068493150682),
         ('HBB1_VAREX', 'HBB1_ANAMI', 0.48275862068965519),
         ('HBB1_VAREX', 'HBB1_CYGMA', 0.4863013698630137),
         ('HBB1_VAREX', 'HBB1_IGUIG', 0.77397260273972601),
         ('HBB1_VAREX', 'HBB1_MOUSE', 0.6095890410958904),
         ('HBB1_VAREX', 'HBB1_ONCMY', 0.48965517241379308),
         ('HBB1_VAREX', 'HBB1_PAGBO', 0.4726027397260274),
         ('HBB1_VAREX', 'HBB1_RAT', 0.62328767123287676),
         ('HBB1_VAREX', 'HBB1_SPHPU', 0.69178082191780821),
         ('HBB1_VAREX', 'HBB1_TAPTE', 0.62328767123287676),
         ('HBB1_VAREX', 'HBB1_TORMA', 0.35616438356164382),
         ('HBB1_VAREX', 'HBB1_TRICR', 0.4513888888888889),
         ('HBB1_VAREX', 'HBB1_UROHA', 0.59589041095890416),
         ('HBB1_VAREX', 'HBB1_VAREX', 1.0),
         ('HBB1_VAREX', 'HBB1_XENBO', 0.51048951048951052),
         ('HBB1_VAREX', 'HBB1_XENLA', 0.5174825174825175),
         ('HBB1_VAREX', 'HBB1_XENTR', 0.4726027397260274),
         ('HBB1_VAREX', 'MYG_DIDMA', 0.25531914893617019),
         ('HBB1_VAREX', 'MYG_ERIEU', 0.25531914893617019),
         ('HBB1_VAREX', 'MYG_ESCGI', 0.24822695035460993),
         ('HBB1_VAREX', 'MYG_GALCR', 0.24822695035460993),
         ('HBB1_XENBO', 'HBB0_PAGBO', 0.43356643356643354),
         ('HBB1_XENBO', 'HBB1_ANAMI', 0.4460431654676259),
         ('HBB1_XENBO', 'HBB1_CYGMA', 0.45985401459854014),
         ('HBB1_XENBO', 'HBB1_IGUIG', 0.4825174825174825),
         ('HBB1_XENBO', 'HBB1_MOUSE', 0.44444444444444442),
         ('HBB1_XENBO', 'HBB1_ONCMY', 0.40140845070422537),
         ('HBB1_XENBO', 'HBB1_PAGBO', 0.43356643356643354),
         ('HBB1_XENBO', 'HBB1_RAT', 0.45833333333333331),
         ('HBB1_XENBO', 'HBB1_SPHPU', 0.48951048951048953),
         ('HBB1_XENBO', 'HBB1_TAPTE', 0.4861111111111111),
         ('HBB1_XENBO', 'HBB1_TORMA', 0.34482758620689657),
         ('HBB1_XENBO', 'HBB1_TRICR', 0.4861111111111111),
         ('HBB1_XENBO', 'HBB1_UROHA', 0.38461538461538464),
         ('HBB1_XENBO', 'HBB1_VAREX', 0.51048951048951052),
         ('HBB1_XENBO', 'HBB1_XENBO', 1.0),
         ('HBB1_XENBO', 'HBB1_XENLA', 0.96551724137931039),
         ('HBB1_XENBO', 'HBB1_XENTR', 0.76388888888888884),
         ('HBB1_XENBO', 'MYG_DIDMA', 0.32075471698113206),
         ('HBB1_XENBO', 'MYG_ELEMA', 0.27358490566037735),
         ('HBB1_XENBO', 'MYG_ERIEU', 0.32075471698113206),
         ('HBB1_XENBO', 'MYG_GALCR', 0.32075471698113206),
         ('HBB1_XENLA', 'HBB0_PAGBO', 0.44055944055944057),
         ('HBB1_XENLA', 'HBB1_ANAMI', 0.45323741007194246),
         ('HBB1_XENLA', 'HBB1_CYGMA', 0.46715328467153283),
         ('HBB1_XENLA', 'HBB1_IGUIG', 0.48951048951048953),
         ('HBB1_XENLA', 'HBB1_MOUSE', 0.44444444444444442),
         ('HBB1_XENLA', 'HBB1_ONCMY', 0.39436619718309857),
         ('HBB1_XENLA', 'HBB1_PAGBO', 0.44055944055944057),
         ('HBB1_XENLA', 'HBB1_RAT', 0.45833333333333331),
         ('HBB1_XENLA', 'HBB1_SPHPU', 0.4825174825174825),
         ('HBB1_XENLA', 'HBB1_TAPTE', 0.47222222222222221),
         ('HBB1_XENLA', 'HBB1_TORMA', 0.33793103448275863),
         ('HBB1_XENLA', 'HBB1_TRICR', 0.49305555555555558),
         ('HBB1_XENLA', 'HBB1_UROHA', 0.3776223776223776),
         ('HBB1_XENLA', 'HBB1_VAREX', 0.5174825174825175),
         ('HBB1_XENLA', 'HBB1_XENBO', 0.96551724137931039),
         ('HBB1_XENLA', 'HBB1_XENLA', 1.0),
         ('HBB1_XENLA', 'HBB1_XENTR', 0.75),
         ('HBB1_XENLA', 'MYG_DIDMA', 0.32075471698113206),
         ('HBB1_XENLA', 'MYG_ELEMA', 0.26415094339622641),
         ('HBB1_XENLA', 'MYG_ERIEU', 0.32075471698113206),
         ('HBB1_XENLA', 'MYG_ESCGI', 0.28282828282828282),
         ('HBB1_XENLA', 'MYG_GALCR', 0.32075471698113206),
         ('HBB1_XENTR', 'HBB0_PAGBO', 0.4726027397260274),
         ('HBB1_XENTR', 'HBB1_ANAMI', 0.4689655172413793),
         ('HBB1_XENTR', 'HBB1_CYGMA', 0.47945205479452052),
         ('HBB1_XENTR', 'HBB1_IGUIG', 0.49315068493150682),
         ('HBB1_XENTR', 'HBB1_MOUSE', 0.4589041095890411),
         ('HBB1_XENTR', 'HBB1_ONCMY', 0.39310344827586208),
         ('HBB1_XENTR', 'HBB1_PAGBO', 0.47945205479452052),
         ('HBB1_XENTR', 'HBB1_RAT', 0.45205479452054792),
         ('HBB1_XENTR', 'HBB1_SPHPU', 0.4726027397260274),
         ('HBB1_XENTR', 'HBB1_TAPTE', 0.45205479452054792),
         ('HBB1_XENTR', 'HBB1_TORMA', 0.33561643835616439),
         ('HBB1_XENTR', 'HBB1_TRICR', 0.49305555555555558),
         ('HBB1_XENTR', 'HBB1_UROHA', 0.35616438356164382),
         ('HBB1_XENTR', 'HBB1_VAREX', 0.4726027397260274),
         ('HBB1_XENTR', 'HBB1_XENBO', 0.76388888888888884),
         ('HBB1_XENTR', 'HBB1_XENLA', 0.75),
         ('HBB1_XENTR', 'HBB1_XENTR', 1.0),
         ('HBB1_XENTR', 'MYG_DIDMA', 0.2857142857142857),
         ('HBB1_XENTR', 'MYG_ERIEU', 0.27067669172932329),
         ('HBB1_XENTR', 'MYG_ESCGI', 0.27272727272727271),
         ('HBB1_XENTR', 'MYG_GALCR', 0.2781954887218045),
         ('MYG_DIDMA', 'HBB0_PAGBO', 0.22222222222222221),
         ('MYG_DIDMA', 'HBB1_IGUIG', 0.25179856115107913),
         ('MYG_DIDMA', 'HBB1_MOUSE', 0.29655172413793102),
         ('MYG_DIDMA', 'HBB1_ONCMY', 0.25694444444444442),
         ('MYG_DIDMA', 'HBB1_RAT', 0.29655172413793102),
         ('MYG_DIDMA', 'HBB1_TAPTE', 0.26277372262773724),
         ('MYG_DIDMA', 'HBB1_VAREX', 0.25531914893617019),
         ('MYG_DIDMA', 'HBB1_XENBO', 0.32075471698113206),
         ('MYG_DIDMA', 'HBB1_XENLA', 0.32075471698113206),
         ('MYG_DIDMA', 'HBB1_XENTR', 0.2857142857142857),
         ('MYG_DIDMA', 'MYG_DIDMA', 1.0),
         ('MYG_DIDMA', 'MYG_ELEMA', 0.81045751633986929),
         ('MYG_DIDMA', 'MYG_ERIEU', 0.87581699346405228),
         ('MYG_DIDMA', 'MYG_ESCGI', 0.83552631578947367),
         ('MYG_DIDMA', 'MYG_GALCR', 0.83006535947712423),
         ('MYG_ELEMA', 'HBB0_PAGBO', 0.20833333333333334),
         ('MYG_ELEMA', 'HBB1_MOUSE', 0.27586206896551724),
         ('MYG_ELEMA', 'HBB1_RAT', 0.28275862068965518),
         ('MYG_ELEMA', 'HBB1_XENBO', 0.27358490566037735),
         ('MYG_ELEMA', 'HBB1_XENLA', 0.26415094339622641),
         ('MYG_ELEMA', 'MYG_DIDMA', 0.81045751633986929),
         ('MYG_ELEMA', 'MYG_ELEMA', 1.0),
         ('MYG_ELEMA', 'MYG_ERIEU', 0.82352941176470584),
         ('MYG_ELEMA', 'MYG_ESCGI', 0.83552631578947367),
         ('MYG_ELEMA', 'MYG_GALCR', 0.84313725490196079),
         ('MYG_ERIEU', 'HBB0_PAGBO', 0.21527777777777779),
         ('MYG_ERIEU', 'HBB1_IGUIG', 0.28368794326241137),
         ('MYG_ERIEU', 'HBB1_MOUSE', 0.30344827586206896),
         ('MYG_ERIEU', 'HBB1_ONCMY', 0.2361111111111111),
         ('MYG_ERIEU', 'HBB1_RAT', 0.29655172413793102),
         ('MYG_ERIEU', 'HBB1_TAPTE', 0.27007299270072993),
         ('MYG_ERIEU', 'HBB1_UROHA', 0.27927927927927926),
         ('MYG_ERIEU', 'HBB1_VAREX', 0.25531914893617019),
         ('MYG_ERIEU', 'HBB1_XENBO', 0.32075471698113206),
         ('MYG_ERIEU', 'HBB1_XENLA', 0.32075471698113206),
         ('MYG_ERIEU', 'HBB1_XENTR', 0.27067669172932329),
         ('MYG_ERIEU', 'MYG_DIDMA', 0.87581699346405228),
         ('MYG_ERIEU', 'MYG_ELEMA', 0.82352941176470584),
         ('MYG_ERIEU', 'MYG_ERIEU', 1.0),
         ('MYG_ERIEU', 'MYG_ESCGI', 0.83552631578947367),
         ('MYG_ERIEU', 'MYG_GALCR', 0.85620915032679734),
         ('MYG_ESCGI', 'HBB0_PAGBO', 0.25),
         ('MYG_ESCGI', 'HBB1_CYGMA', 0.2361111111111111),
         ('MYG_ESCGI', 'HBB1_IGUIG', 0.27659574468085107),
         ('MYG_ESCGI', 'HBB1_MOUSE', 0.28965517241379313),
         ('MYG_ESCGI', 'HBB1_ONCMY', 0.25),
         ('MYG_ESCGI', 'HBB1_RAT', 0.28275862068965518),
         ('MYG_ESCGI', 'HBB1_TAPTE', 0.3611111111111111),
         ('MYG_ESCGI', 'HBB1_TORMA', 0.25675675675675674),
         ('MYG_ESCGI', 'HBB1_VAREX', 0.24822695035460993),
         ('MYG_ESCGI', 'HBB1_XENLA', 0.28282828282828282),
         ('MYG_ESCGI', 'HBB1_XENTR', 0.27272727272727271),
         ('MYG_ESCGI', 'MYG_DIDMA', 0.83552631578947367),
         ('MYG_ESCGI', 'MYG_ELEMA', 0.83552631578947367),
         ('MYG_ESCGI', 'MYG_ERIEU', 0.83552631578947367),
         ('MYG_ESCGI', 'MYG_ESCGI', 1.0),
         ('MYG_ESCGI', 'MYG_GALCR', 0.84210526315789469),
         ('MYG_GALCR', 'HBB0_PAGBO', 0.24305555555555555),
         ('MYG_GALCR', 'HBB1_IGUIG', 0.28368794326241137),
         ('MYG_GALCR', 'HBB1_MOUSE', 0.28275862068965518),
         ('MYG_GALCR', 'HBB1_ONCMY', 0.24305555555555555),
         ('MYG_GALCR', 'HBB1_RAT', 0.27586206896551724),
         ('MYG_GALCR', 'HBB1_TAPTE', 0.27007299270072993),
         ('MYG_GALCR', 'HBB1_VAREX', 0.24822695035460993),
         ('MYG_GALCR', 'HBB1_XENBO', 0.32075471698113206),
         ('MYG_GALCR', 'HBB1_XENLA', 0.32075471698113206),
         ('MYG_GALCR', 'HBB1_XENTR', 0.2781954887218045),
         ('MYG_GALCR', 'MYG_DIDMA', 0.83006535947712423),
         ('MYG_GALCR', 'MYG_ELEMA', 0.84313725490196079),
         ('MYG_GALCR', 'MYG_ERIEU', 0.85620915032679734),
         ('MYG_GALCR', 'MYG_ESCGI', 0.84210526315789469),
         ('MYG_GALCR', 'MYG_GALCR', 1.0),
         ('PRCA_ANASP', 'PRCA_ANASP', 1.0),
         ('PRCA_ANASP', 'PRCA_ANAVA', 0.97222222222222221),
         ('PRCA_ANAVA', 'PRCA_ANASP', 0.97222222222222221),
         ('PRCA_ANAVA', 'PRCA_ANAVA', 1.0)]

###

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = doctests_test
"""
Run all of the doctests in the doc/*.rest files.
"""
import os.path
import doctest
import unittest

from testlib import testutil


def codetest():
    "Test the code here before adding to doctest @CTB"
    import pygr
    from pygr.seqdb import SequenceFileDB
    db = SequenceFileDB(os.path.join('data', 'partial-yeast.fasta'))
    chr02 = db['chr02']
    start, stop = (87787, 86719)
    x = chr02[start:stop]


def get_suite():
    suite = unittest.TestSuite()

    names = [
#        'contents.rst',
#        'sequences.rst',
#        'contrib%sfetch.rst' % os.path.sep,   @CTB does not work on my system?
#        'recipes%spygrdata_recipes.rst' % os.path.sep,
#        'recipes%salignment_recipes.rst' % os.path.sep,
    ]

    # needs relative paths for some reason
    doctestpath = os.path.join('..', 'doc', 'rest')
    paths = [os.path.join(doctestpath, name) for name in names]

    for path in paths:
        docsuite = doctest.DocFileSuite(path)
        suite.addTest(docsuite)

    return suite


if __name__ == '__main__':
    #codetest()
    suite = get_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

########NEW FILE########
__FILENAME__ = downloadNLMSA_megatest
import ConfigParser
import os.path
import shutil
import tempfile
import threading
import time
import unittest

from pygr import metabase
from pygr.downloader import SourceURL
from pygr.nlmsa_utils import NLMSABuilder
from testlib import megatest_utils, testutil, PygrTestProgram


def create_downloadable_resource(url, mdb, name, doc):
    dfile = SourceURL(url)
    nbuilder = NLMSABuilder(dfile)
    nbuilder.__doc__ = doc
    mdb.add_resource(name, nbuilder)
    mdb.commit()


class NLMSADownload_Test(unittest.TestCase):
    '''Try to download and build a relatively large alignment'''

    def setUp(self):
        config = ConfigParser.ConfigParser({'testOutputBaseDir': '.',
                                            'httpdPort': '28145'})
        config.read([os.path.join(os.path.expanduser('~'), '.pygrrc'),
                     os.path.join(os.path.expanduser('~'), 'pygr.cfg'),
                     '.pygrrc', 'pygr.cfg'])
        httpdPort = config.get('megatests_download', 'httpdPort')
        httpdServedFile = config.get('megatests_download', 'httpdServedFile')
        testOutputBaseDir = config.get('megatests', 'testOutputBaseDir')

        self.resource_name = 'Test.NLMSA'

        server_addr = ('127.0.0.1', int(httpdPort)) # FIXME: randomise the port?
        self.httpd = megatest_utils.HTTPServerLauncher(server_addr,
                                                       httpdServedFile)
        server_thread = threading.Thread(target=self.httpd.run)
        server_thread.setDaemon(True)
        server_thread.start()

        self.test_dir = tempfile.mkdtemp(dir=testOutputBaseDir,
                                         prefix='megatest')
        dl_dir = os.path.join(self.test_dir, 'dl')
        os.mkdir(dl_dir)
        if 'WORLDBASEDOWNLOAD' in os.environ:
            self.old_download = os.environ['WORLDBASEDOWNLOAD']
        else:
            self.old_download = None
        os.environ['WORLDBASEDOWNLOAD'] = self.test_dir
        if 'WORLDBASEBUILDDIR' in os.environ:
            self.old_builddir = os.environ['WORLDBASEBUILDDIR']
        else:
            self.old_builddir = None
        os.environ['WORLDBASEBUILDDIR'] = self.test_dir

        self.mdb = metabase.MetabaseList(self.test_dir)
        self.mdb_dl = metabase.MetabaseList(dl_dir)
        url = 'http://%s:%d/' % server_addr + os.path.basename(httpdServedFile)
        create_downloadable_resource(url, self.mdb_dl, self.resource_name,
                                     'An example downloadable NLMSA')

    def test_download(self):
        'Test downloading NLMSA data'
        t = time.time()
        msa_dl = self.mdb_dl(self.resource_name)  # download and build it!
        t1 = time.time() - t
        t = time.time()
        self.mdb.add_resource(self.resource_name, msa_dl)
        self.mdb.commit()
        del msa_dl
        msa = self.mdb(self.resource_name)  # already built
        t2 = time.time() - t
        assert t2 < t1/3., 'second request took too long!'
        chr4 = msa.seqDict['dm2.chr4']
        result = msa[chr4[:10000]]
        assert len(result) == 9

    def tearDown(self):
        # Just in case - the server thread is daemonic so it will get
        # terminated when the main one finishes.
        self.httpd.request_shutdown()
        if self.old_download is not None:
            os.environ['WORLDBASEDOWNLOAD'] = self.old_download
        else:
            del os.environ['WORLDBASEDOWNLOAD']
        if self.old_builddir is not None:
            os.environ['WORLDBASEBUILDDIR'] = self.old_builddir
        else:
            del os.environ['WORLDBASEBUILDDIR']
        shutil.rmtree(self.test_dir)


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = graph_test
"""
Test some of the basics underpinning the graph system.
"""

import os
import unittest

from testlib import testutil, PygrTestProgram, SkipTest
from pygr import mapping, graphquery, sqlgraph


class Node(object):

    def __init__(self, id):
        self.id = id


class Query_Test(unittest.TestCase):
    "Pygr Query tests"

    def get_node(self, k):
        try:
            db = self.nodeDB
        except AttributeError:
            return k
        else:
            try:
                return db[k]
            except KeyError:
                db[k] = Node(k)
                return db[k]

    def node_graph(self, g):
        try:
            db = self.nodeDB
        except AttributeError:
            return g
        out = {}
        for k, e in g.items():
            k = self.get_node(k)
            d = out.setdefault(k, {})
            for dest, edge in e.items():
                d[self.get_node(dest)] = edge
        return out

    def node_list(self, l):
        try:
            db = self.nodeDB
        except AttributeError:
            return l
        out = []
        for k in l:
            out.append(self.get_node(k))
        return out

    def node_result(self, r):
        try:
            db = self.nodeDB
        except AttributeError:
            return r
        l = []
        for d in r:
            d2 = {}
            for k, v in d.items():
                d2[k] = self.get_node(v)
            l.append(d2)
        return l

    def update_graph(self, datagraph):
        try:
            g = self.datagraph
        except AttributeError:
            return datagraph
        else:
            g.update(datagraph)
            return g

    def dqcmp(self, datagraph, querygraph, result):
        datagraph = self.update_graph(self.node_graph(datagraph))
        l = [d.copy() for d in graphquery.GraphQuery(datagraph, querygraph)]
        assert len(l) == len(result), 'length mismatch'
        l.sort()
        result = self.node_result(result)
        result.sort()
        for i in range(len(l)):
            assert l[i] == result[i], 'incorrect result'

    def test_basicquery_test(self):
        "Basic query"
        datagraph = {0: {1: None, 2: None, 3: None},
                     1: {2: None}, 3: {4: None, 5: None},
                     4: {6: None}, 5: {6: None}, 2: {}, 6: {}}
        querygraph = {0: {1: None, 2: None, 3: None},
                      3: {4: None}, 1: {}, 2: {}, 4: {}}
        result = [{0: 0, 1: 1, 2: 2, 3: 3, 4: 4},
                  {0: 0, 1: 1, 2: 2, 3: 3, 4: 5},
                  {0: 0, 1: 2, 2: 1, 3: 3, 4: 4},
                  {0: 0, 1: 2, 2: 1, 3: 3, 4: 5}]

        self.dqcmp(datagraph, querygraph, result)

    def test_iter(self):
        'test basic iteration'
        g = {0: {1: None, 2: None, 3: None},
             1: {2: None}, 3: {4: None, 5: None},
             4: {6: None}, 5: {6: None}, 2: {}, 6: {}}
        datagraph = self.update_graph(self.node_graph(g))
        l = list(iter(datagraph))
        l.sort()
        result = self.node_list([0, 1, 2, 3, 4, 5, 6])
        result.sort()
        assert l == result

    def test_cyclicquery(self):
        "Cyclic QG against cyclic DG @CTB comment?"
        datagraph = {1: {2: None}, 2: {3: None}, 3: {4: None}, 4: {5: None},
                      5: {2: None}}
        querygraph = {0: {1: None}, 1: {2: None}, 2: {4: None}, 3: {1: None},
                      4: {3: None}}
        result = [{0: 1, 1: 2, 2: 3, 3: 5, 4: 4}]
        self.dqcmp(datagraph, querygraph, result)

    def test_cyclicacyclicquery(self):
        "Cyclic QG against acyclic DG"
        datagraph = {0: {1: None}, 1: {3: None}, 5: {3: None}, 4: {5: None},
                     2: {4: None, 1: None}, 3: {}}
        querygraph = {0: {1: None}, 1: {3: None}, 3: {5: None}, 5: {4: None},
                      4: {2: None}, 2: {1: None}}
        result = []
        self.dqcmp(datagraph, querygraph, result)

    def test_symmetricquery_test(self):
        "Symmetrical QG against symmetrical DG"
        datagraph = {1: {2: None}, 2: {3: None, 4: None}, 5: {2: None},
                     3: {}, 4: {}}
        querygraph = {0: {1: None}, 1: {2: None}, 2: {}}
        result = [{0: 1, 1: 2, 2: 3}, {0: 1, 1: 2, 2: 4},
                  {0: 5, 1: 2, 2: 3}, {0: 5, 1: 2, 2: 4}]
        self.dqcmp(datagraph, querygraph, result)

    def test_filteredquery(self):
        "Test a filter against a query"
        datagraph = {0: {1: None, 2: None, 3: None}, 1: {2: None, 3: None},
                     3: {4: None}}
        querygraph = {0: {1: {'filter': lambda toNode, **kw:
                              toNode == self.get_node(3)}}, 1: {}}
        result = [{0: 0, 1: 3}, {0: 1, 1: 3}]
        self.dqcmp(datagraph, querygraph, result)

    def test_headlessquery(self):
        "Test a query with no head nodes"
        datagraph = {0: {1: None}, 1: {2: None}, 2: {3: None}, 3: {4: None},
                     4: {1: None}}
        querygraph = {0: {1: None}, 1: {2: None}, 2: {3: None}, 3: {0: None}}
        result = [{0: 1, 1: 2, 2: 3, 3: 4},
                  {0: 2, 1: 3, 2: 4, 3: 1},
                  {0: 3, 1: 4, 2: 1, 3: 2},
                  {0: 4, 1: 1, 2: 2, 3: 3}]
        self.dqcmp(datagraph, querygraph, result)


class Mapping_Test(Query_Test):
    "Tests mappings"

    def setUp(self):
        self.datagraph = mapping.dictGraph()

    def test_graphdict(self):
        "Graph dictionary"
        datagraph = self.datagraph
        datagraph += self.get_node(1)
        datagraph[self.get_node(1)] += self.get_node(2)
        results = {1: {2: None}, 2: {}}
        results = self.node_graph(results)
        assert datagraph == results, 'incorrect result'

    def test_nodedel(self):
        "Node deletion"
        datagraph = self.datagraph
        datagraph += self.get_node(1)
        datagraph += self.get_node(2)
        datagraph[self.get_node(2)] += self.get_node(3)
        datagraph -= self.get_node(1)
        results = {2: {3: None}, 3: {}}
        results = self.node_graph(results)
        assert datagraph == results, 'incorrect result'

    def test_delraise(self):
        "Delete raise"
        datagraph = self.datagraph
        datagraph += self.get_node(1)
        datagraph += self.get_node(2)
        datagraph[self.get_node(2)] += self.get_node(3)
        try:
            for i in range(0, 2):
                datagraph -= self.get_node(3)
            raise ValueError('failed to catch bad node deletion attempt')
        except KeyError:
            pass # THIS IS THE CORRECT RESULT

    def test_setitemraise(self):
        "Setitemraise"
        datagraph = self.datagraph
        datagraph += self.get_node(1)
        try:
            datagraph[self.get_node(1)] = self.get_node(2)
            raise KeyError('failed to catch bad setitem attempt')
        except ValueError:
            pass # THIS IS THE CORRECT RESULT

    def test_graphedges(self):
        "Graphedges"
        datagraph = self.datagraph
        graphvals = {1: {2: None}, 2: {3: None, 4: None}, 5: {2: None},
                     3: {}, 4: {}}
        graphvals = self.node_graph(graphvals)
        edge_list = [[self.get_node(1), self.get_node(2), None],
                     [self.get_node(2), self.get_node(3), None],
                     [self.get_node(2), self.get_node(4), None],
                     [self.get_node(5), self.get_node(2), None]]
        for i in graphvals:
            datagraph += i
            for n in graphvals[i].keys():
                datagraph[i] += n
        edge_results = []
        for e in datagraph.edges():
            edge_results.append(e)
        edge_results.sort()
        edge_results = [list(t) for t in edge_results]
        edge_list.sort()
        #print 'edge_results:', edge_results
        assert edge_results == edge_list, 'incorrect result'


class Graph_Test(Mapping_Test):
    "Run same tests on mapping.Graph class"

    def setUp(self):
        self.datagraph = mapping.Graph()


class Graph_DB_Test(Mapping_Test):
    "test mapping.Graph with sourceDB, targetDB but no edgeDB"

    def setUp(self):
        self.nodeDB = {1: Node(1), 2: Node(2)}
        self.datagraph = mapping.Graph(sourceDB=self.nodeDB,
                                       targetDB=self.nodeDB)

    def test_no_edge_db(self):
        'test behavior with no edgeDB'
        self.datagraph += self.nodeDB[1] # add node
        self.datagraph[self.nodeDB[1]][self.nodeDB[2]] = 3 # add edge

        assert self.datagraph[self.nodeDB[1]][self.nodeDB[2]] == 3


class GraphShelve_Test(Mapping_Test):
    "Run same tests on mapping.Graph class"

    def setUp(self):

        tmp = testutil.TempDir('graphshelve-test')
        filename = tmp.subfile() # needs a random name each time
        self.datagraph = mapping.Graph(filename=filename, intKeys=True)

    def tearDown(self):
        self.datagraph.close()


class GraphShelve_DB_Test(Mapping_Test):
    "Run same tests on mapping.Graph class"

    def setUp(self):
        self.nodeDB = {}
        tmp = testutil.TempDir('graphshelve-test')
        filename = tmp.subfile() # needs a random name each time
        self.datagraph = mapping.Graph(sourceDB=self.nodeDB,
                                       targetDB=self.nodeDB,
                                       filename=filename, intKeys=True)

    def tearDown(self):
        self.datagraph.close()


class SQLGraph_Test(Mapping_Test):
    "Runs the same tests on mapping.SQLGraph class"
    dbname = 'test.dumbo_foo_test'

    def setUp(self):
        if not testutil.mysql_enabled():
            raise SkipTest("no MySQL")

        createOpts = dict(source_id='int', target_id='int', edge_id='int')
        self.datagraph = sqlgraph.SQLGraph(self.dbname, dropIfExists=True,
                                           createTable=createOpts)

    def tearDown(self):
        self.datagraph.cursor.execute('drop table if exists %s' % self.dbname)


class SQLGraph_DB_Test(Mapping_Test):
    "Runs the same tests on mapping.SQLGraph class"
    dbname = 'test.dumbo_foo_test'

    def setUp(self):
        if not testutil.mysql_enabled():
            raise SkipTest("no MySQL")

        self.nodeDB = {}
        createOpts = dict(source_id='int', target_id='int', edge_id='int')
        self.datagraph = sqlgraph.SQLGraph(self.dbname, dropIfExists=True,
                                           createTable=createOpts,
                                           sourceDB=self.nodeDB,
                                           targetDB=self.nodeDB)

    def tearDown(self):
        self.datagraph.cursor.execute('drop table if exists %s' % self.dbname)


class SQLiteGraph_Test(testutil.SQLite_Mixin, Mapping_Test):
    'run same tests on mapping.SQLGraph class using sqlite'

    def sqlite_load(self):
        createOpts = dict(source_id='int', target_id='int', edge_id='int')
        self.datagraph = sqlgraph.SQLGraph('testgraph',
                                           serverInfo=self.serverInfo,
                                           dropIfExists=True,
                                           createTable=createOpts)


class SQLiteGraph_DB_Test(testutil.SQLite_Mixin, Mapping_Test):
    'run same tests on mapping.SQLGraph class using sqlite'

    def sqlite_load(self):
        self.nodeDB = {}
        createOpts = dict(source_id='int', target_id='int', edge_id='int')
        self.datagraph = sqlgraph.SQLGraph('testgraph',
                                           serverInfo=self.serverInfo,
                                           dropIfExists=True,
                                           createTable=createOpts,
                                           sourceDB=self.nodeDB,
                                           targetDB=self.nodeDB)

# test currently unused, requires access to leelab data
## from pygr import worldbase
## class Splicegraph_Test(unittest.TestCase):

##     def setUp(self):
##         self.sg = worldbase.Bio.Annotation.ASAP2.Isoform.HUMAN.\
##                   hg17.splicegraph()

##     def exonskip_megatest(self):
##         'perform exon skip query'
##         query = {0:{1:None,2:None},1:{2:None},2:{}}
##         gq = graphquery.GraphQuery(self.sg, query)
##         l = list(gq)
##         assert len(l) == 11546, 'test exact size of exonskip set'

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = metabase_test
import datetime
import os
import pickle
import socket
import unittest

from testlib import testutil, PygrTestProgram, SkipTest
from pygr import seqdb, cnestedlist, metabase, mapping, logger, sqlgraph
from pygr.downloader import SourceURL, GenericBuilder, uncompress_file, \
     do_unzip, do_gunzip

try:
    set
except NameError:
    from sets import Set as set


class TestBase(unittest.TestCase):
    "A base class to all metabase test classes"

    def setUp(self, worldbasePath=None, **kwargs):
        # overwrite the WORLDBASEPATH environment variable
        self.tempdir = testutil.TempDir('pygrdata')
        if worldbasePath is None:
            worldbasePath = self.tempdir.path
        self.metabase = metabase.MetabaseList(worldbasePath, **kwargs)
        self.pygrData = self.metabase.Data
        self.schema = self.metabase.Schema
        # handy shortcuts
        self.EQ = self.assertEqual


class Download_Test(TestBase):
    "Save seq db and interval to metabase shelve"

    # tested elsewhere as well, on Linux makes gzip ask for permissions
    # to overwrite
    def test_download(self):
        "Downloading of gzipped file using metabase"

        url = SourceURL('http://www.doe-mbi.ucla.edu/~leec/test.gz')
        url.__doc__ = 'test download'

        self.metabase.add_resource('Bio.Test.Download1', url)
        self.metabase.commit()

        # performs the download
        fpath = self.pygrData.Bio.Test.Download1()
        h = testutil.get_file_md5(fpath)
        self.assertEqual(h.hexdigest(), 'f95656496c5182d6cff9a56153c9db73')
        os.remove(fpath)

    def test_run_unzip(self):
        'test uncompress_file unzip'
        zipfile = testutil.datafile('test.zip')
        outfile = testutil.tempdatafile('test.out')
        uncompress_file(zipfile, newpath=outfile, singleFile=True)
        h = testutil.get_file_md5(outfile)
        self.assertEqual(h.hexdigest(), '12ada4c51ccb4c7277c16f1a3c000b90')

    def test_do_unzip(self):
        'test do_unzip'
        zipfile = testutil.datafile('test.zip')
        outfile = testutil.tempdatafile('test2.out')
        do_unzip(zipfile, outfile, singleFile=True)
        h = testutil.get_file_md5(outfile)
        self.assertEqual(h.hexdigest(), '12ada4c51ccb4c7277c16f1a3c000b90')

    def test_run_gunzip(self):
        'test uncompress_file gunzip'
        zipfile = testutil.datafile('test.gz')
        outfile = testutil.tempdatafile('test3.out')
        uncompress_file(zipfile, newpath=outfile)
        h = testutil.get_file_md5(outfile)
        self.assertEqual(h.hexdigest(), '1db5a21a01ba465fd26c3203d6589b0e')

    def test_do_gunzip(self):
        'test do_gunzip'
        zipfile = testutil.datafile('test.gz')
        outfile = testutil.tempdatafile('test4.out')
        do_gunzip(zipfile, outfile)
        h = testutil.get_file_md5(outfile)
        self.assertEqual(h.hexdigest(), '1db5a21a01ba465fd26c3203d6589b0e')


class GenericBuild_Test(TestBase):

    def test_generic_build(self):
        "GenericBuilder construction of the BlastDB"

        sp_hbb1 = testutil.datafile('sp_hbb1')
        gb = GenericBuilder('BlastDB', sp_hbb1)
        s = pickle.dumps(gb)
        db = pickle.loads(s) # force construction of the BlastDB
        self.EQ(len(db), 24)

        found = [x for x in db]
        found.sort()

        expected = ['HBB0_PAGBO', 'HBB1_ANAMI', 'HBB1_CYGMA', 'HBB1_IGUIG',
                   'HBB1_MOUSE', 'HBB1_ONCMY', 'HBB1_PAGBO', 'HBB1_RAT',
                   'HBB1_SPHPU', 'HBB1_TAPTE', 'HBB1_TORMA', 'HBB1_TRICR',
                   'HBB1_UROHA', 'HBB1_VAREX', 'HBB1_XENBO', 'HBB1_XENLA',
                   'HBB1_XENTR', 'MYG_DIDMA', 'MYG_ELEMA', 'MYG_ERIEU',
                   'MYG_ESCGI', 'MYG_GALCR', 'PRCA_ANASP', 'PRCA_ANAVA']
        expected.sort()

        self.EQ(expected, found)


class DNAAnnotation_Test(TestBase):

    def setUp(self, **kwargs):
        TestBase.setUp(self)
        dnaseq = testutil.datafile('dnaseq.fasta')
        tryannot = testutil.tempdatafile('tryannot')

        db = seqdb.BlastDB(dnaseq)
        try:
            db.__doc__ = 'little dna'

            self.pygrData.Bio.Test.dna = db
            annoDB = seqdb.AnnotationDB({1: ('seq1', 5, 10, 'fred'),
                                         2: ('seq1', -60, -50, 'bob'),
                                         3: ('seq2', -20, -10, 'mary')},
                                        db,
                                  sliceAttrDict=dict(id=0, start=1, stop=2,
                                                     name=3))
            annoDB.__doc__ = 'trivial annotation'
            self.pygrData.Bio.Test.annoDB = annoDB
            nlmsa = cnestedlist.NLMSA(tryannot, 'w', pairwiseMode=True,
                                      bidirectional=False)
            try:
                for annID in annoDB:
                    nlmsa.addAnnotation(annoDB[annID])

                nlmsa.build()
                nlmsa.__doc__ = 'trivial map'
                self.pygrData.Bio.Test.map = nlmsa
                self.schema.Bio.Test.map = metabase.ManyToManyRelation(db,
                                                 annoDB, bindAttrs=('exons', ))
                self.metabase.commit()
                self.metabase.clear_cache()
            finally:
                nlmsa.close()
        finally:
            db.close()

    def test_annotation(self):
        "Annotation test"
        db = self.pygrData.Bio.Test.dna()
        try:
            s1 = db['seq1']
            l = s1.exons.keys()
            annoDB = self.pygrData.Bio.Test.annoDB()
            assert l == [annoDB[1], -(annoDB[2])]
            assert l[0].sequence == s1[5:10]
            assert l[1].sequence == s1[50:60]
            assert l[0].name == 'fred', 'test annotation attribute access'
            assert l[1].name == 'bob'
            sneg = -(s1[:55])
            l = sneg.exons.keys()
            assert l == [annoDB[2][5:], -(annoDB[1])]
            assert l[0].sequence == -(s1[50:55])
            assert l[1].sequence == -(s1[5:10])
            assert l[0].name == 'bob'
            assert l[1].name == 'fred'
        finally:
            db.close() # close SequenceFileDB
            self.pygrData.Bio.Test.map().close() # close NLMSA


def populate_swissprot(pygrData, pygrDataSchema):
    "Populate the current pygrData with swissprot data"
    # build BlastDB out of the sequences
    sp_hbb1 = testutil.datafile('sp_hbb1')
    sp = seqdb.BlastDB(sp_hbb1)
    sp.__doc__ = 'little swissprot'
    pygrData.Bio.Seq.Swissprot.sp42 = sp

    # also store a fragment
    hbb = sp['HBB1_TORMA']
    ival= hbb[10:35]
    ival.__doc__ = 'fragment'
    pygrData.Bio.Seq.frag = ival

    # build a mapping to itself
    m = mapping.Mapping(sourceDB=sp, targetDB=sp)
    trypsin = sp['PRCA_ANAVA']
    m[hbb] = trypsin
    m.__doc__ = 'map sp to itself'
    pygrData.Bio.Seq.spmap = m

    # create an annotation database and bind as exons attribute
    pygrDataSchema.Bio.Seq.spmap = metabase.OneToManyRelation(sp, sp,
                                                         bindAttrs=('buddy', ))
    annoDB = seqdb.AnnotationDB({1: ('HBB1_TORMA', 10, 50)}, sp,
                                sliceAttrDict=dict(id=0, start=1, stop=2))
    exon = annoDB[1]

    # generate the names where these will be stored
    tempdir = testutil.TempDir('exonAnnot')
    filename = tempdir.subfile('cnested')
    nlmsa = cnestedlist.NLMSA(filename, 'w', pairwiseMode=True,
                              bidirectional=False)
    nlmsa.addAnnotation(exon)
    nlmsa.build()
    annoDB.__doc__ = 'a little annotation db'
    nlmsa.__doc__ = 'a little map'
    pygrData.Bio.Annotation.annoDB = annoDB
    pygrData.Bio.Annotation.map = nlmsa
    pygrDataSchema.Bio.Annotation.map = \
         metabase.ManyToManyRelation(sp, annoDB, bindAttrs=('exons', ))


def check_match(self):
    frag = self.pygrData.Bio.Seq.frag()
    correct = self.pygrData.Bio.Seq.Swissprot.sp42()['HBB1_TORMA'][10:35]
    assert frag == correct, 'seq ival should match'
    assert frag.__doc__ == 'fragment', 'docstring should match'
    assert str(frag) == 'IQHIWSNVNVVEITAKALERVFYVY', 'letters should match'
    assert len(frag) == 25, 'length should match'
    assert len(frag.path) == 142, 'length should match'

    #store = PygrDataTextFile('results/seqdb1.pickle')
    #saved = store['hbb1 fragment']
    #assert frag == saved, 'seq ival should matched stored result'


def check_dir(self):
    expected=['Bio.Annotation.annoDB', 'Bio.Annotation.map',
                'Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap']
    expected.sort()
    found = self.metabase.dir('Bio')
    found.sort()
    assert found == expected


def check_dir_noargs(self):
    found = self.metabase.dir()
    found.sort()
    found2 = self.metabase.dir('')
    found2.sort()
    assert found == found2


def check_dir_download(self):
    found = self.metabase.dir(download=True)
    found.sort()
    found2 = self.metabase.dir('', download=True)
    found2.sort()
    assert len(found) == 0
    assert found == found2


def check_dir_re(self):
    expected=['Bio.Annotation.annoDB', 'Bio.Annotation.map',
                'Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap']
    expected.sort()
    found = self.metabase.dir('^Bio', 'r')
    found.sort()
    assert found == expected

    expected = ['Bio.Seq.Swissprot.sp42', 'Bio.Seq.spmap']
    expected.sort()
    found = self.metabase.dir('^Bio\..+\.sp', 'r')
    found.sort()
    assert found == expected


def check_bind(self):
    sp = self.pygrData.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    trypsin = sp['PRCA_ANAVA']
    assert hbb.buddy == trypsin, 'automatic schema attribute binding'


def check_bind2(self):
    sp = self.pygrData.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    exons = hbb.exons.keys()
    assert len(exons)==1, 'number of expected annotations'
    annoDB = self.pygrData.Bio.Annotation.annoDB()
    exon = annoDB[1]
    assert exons[0] == exon, 'test annotation comparison'
    assert exons[0].pathForward is exon, 'annotation parent match'
    assert exons[0].sequence == hbb[10:50], 'annotation to sequence match'
    onc = sp['HBB1_ONCMY']
    try:
        exons = onc.exons.keys()
        raise ValueError('failed to catch query with no annotations')
    except KeyError:
        pass


class Sequence_Test(TestBase):

    def setUp(self, *args, **kwargs):
        TestBase.setUp(self, *args, **kwargs)
        populate_swissprot(self.pygrData, self.schema)
        self.metabase.commit() # finally save everything
        self.metabase.clear_cache() # force all requests to reload

    def test_match(self):
        "Test matching sequences"
        check_match(self)

    def test_dir(self):
        "Test labels"
        check_dir(self)
        check_dir_noargs(self)
        check_dir_re(self)

    def test_bind(self):
        "Test bind"
        check_bind(self)
        check_bind2(self)

    def test_schema(self):
        "Test schema"
        sp_hbb1 = testutil.datafile('sp_hbb1')
        sp2 = seqdb.BlastDB(sp_hbb1)
        sp2.__doc__ = 'another sp'
        self.pygrData.Bio.Seq.sp2 = sp2
        sp = self.pygrData.Bio.Seq.Swissprot.sp42()
        m = mapping.Mapping(sourceDB=sp, targetDB=sp2)
        m.__doc__ = 'sp -> sp2'
        self.pygrData.Bio.Seq.testmap = m
        self.schema.Bio.Seq.testmap = metabase.OneToManyRelation(sp, sp2)
        self.metabase.commit()

        self.metabase.clear_cache()

        sp3 = seqdb.BlastDB(sp_hbb1)
        sp3.__doc__ = 'sp number 3'
        self.pygrData.Bio.Seq.sp3 = sp3
        sp2 = self.pygrData.Bio.Seq.sp2()
        m = mapping.Mapping(sourceDB=sp3, targetDB=sp2)
        m.__doc__ = 'sp3 -> sp2'
        self.pygrData.Bio.Seq.testmap2 = m
        self.schema.Bio.Seq.testmap2 = metabase.OneToManyRelation(sp3, sp2)
        l = self.metabase.resourceCache.keys()
        l.sort()
        assert l == ['Bio.Seq.sp2', 'Bio.Seq.sp3', 'Bio.Seq.testmap2']
        self.metabase.commit()
        g = self.metabase.writer.storage.graph
        expected = set(['Bio.Annotation.annoDB',
                     'Bio.Seq.Swissprot.sp42', 'Bio.Seq.sp2', 'Bio.Seq.sp3'])
        found = set(g.keys())
        self.EQ(len(expected - found), 0)


class SQL_Sequence_Test(Sequence_Test):

    def setUp(self):
        if not testutil.mysql_enabled():
            raise SkipTest

        self.dbtable = testutil.temp_table_name() # create temp db tables
        Sequence_Test.setUp(self, worldbasePath='mysql:' + self.dbtable,
                            mdbArgs=dict(createLayer='temp'))

    def tearDown(self):
        testutil.drop_tables(self.metabase.writer.storage.cursor, self.dbtable)


class InvalidPickle_Test(TestBase):

    def setUp(self):
        TestBase.setUp(self)

        class MyUnpicklableClass(object):
            pass

        MyUnpicklableClass.__module__ = '__main__'
        self.bad = MyUnpicklableClass()

        self.good = datetime.datetime.today()

    def test_invalid_pickle(self):
        "Testing an invalid pickle"
        s = metabase.dumps(self.good) # should pickle with no errors
        try:
            s = metabase.dumps(self.bad) # should raise exception
            msg = 'failed to catch bad attempt to invalid module ref'
            raise ValueError(msg)
        except metabase.WorldbaseNoModuleError:
            pass


class DBServerInfo_Test(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        logger.debug('accessing ensembldb.ensembl.org')
        conn = sqlgraph.DBServerInfo(host='ensembldb.ensembl.org',
                                     user='anonymous', passwd='')
        try:
            translationDB = sqlgraph.SQLTable(
                'homo_sapiens_core_47_36i.translation', serverInfo=conn)
            exonDB = sqlgraph.SQLTable('homo_sapiens_core_47_36i.exon',
                                       serverInfo=conn)

            sql_statement = '''SELECT t3.exon_id FROM
homo_sapiens_core_47_36i.translation AS tr,
homo_sapiens_core_47_36i.exon_transcript AS t1,
homo_sapiens_core_47_36i.exon_transcript AS t2,
homo_sapiens_core_47_36i.exon_transcript AS t3 WHERE tr.translation_id = %s
AND tr.transcript_id = t1.transcript_id AND t1.transcript_id =
t2.transcript_id AND t2.transcript_id = t3.transcript_id AND t1.exon_id =
tr.start_exon_id AND t2.exon_id = tr.end_exon_id AND t3.rank >= t1.rank AND
t3.rank <= t2.rank ORDER BY t3.rank
'''
            translationExons = sqlgraph.GraphView(translationDB, exonDB,
                                                  sql_statement,
                                                  serverInfo=conn)
        except ImportError:
            raise SkipTest('missing MySQLdb module?')
        translationExons.__doc__ = 'test saving exon graph'
        self.pygrData.Bio.Ensembl.TranslationExons = translationExons
        self.metabase.commit()
        self.metabase.clear_cache()

    def test_orderBy(self):
        """Test saving DBServerInfo to metabase"""
        translationExons = self.pygrData.Bio.Ensembl.TranslationExons()
        translation = translationExons.sourceDB[15121]
        exons = translationExons[translation] # do the query
        result = [e.id for e in exons]
        correct = [95160, 95020, 95035, 95050, 95059, 95069, 95081, 95088,
                   95101, 95110, 95172]
        self.assertEqual(result, correct) # make sure the exact order matches


class XMLRPC_Test(TestBase):
    'create an XMLRPC server and access seqdb from it'

    def setUp(self):
        TestBase.setUp(self)
        populate_swissprot(self.pygrData, self.schema) # save some data
        self.metabase.commit() # finally save everything
        self.metabase.clear_cache() # force all requests to reload

        res = ['Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap',
               'Bio.Annotation.annoDB', 'Bio.Annotation.map']
        self.server = testutil.TestXMLRPCServer(res, self.tempdir.path)

    def test_xmlrpc(self):
        "Test XMLRPC"
        self.metabase.clear_cache() # force all requests to reload
        self.metabase.update("http://localhost:%s" % self.server.port)

        check_match(self)
        check_dir(self)
        check_dir_noargs(self)
        check_dir_download(self)
        check_dir_re(self)
        check_bind(self)
        check_bind2(self)

        sb_hbb1 = testutil.datafile('sp_hbb1')
        sp2 = seqdb.BlastDB(sb_hbb1)
        sp2.__doc__ = 'another sp'
        try:
            self.pygrData.Bio.Seq.sp2 = sp2
            self.metabase.commit()
            msg = 'failed to catch bad attempt to write to XMLRPC server'
            raise KeyError(msg)
        except ValueError:
            pass

    def tearDown(self):
        'halt the test XMLRPC server'
        self.server.close()


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = nlmsa_dm2_megatest
import unittest
from testlib import testutil, PygrTestProgram

import ConfigParser
import glob
import os
import string
import sys

import pygr.Data

try:
    import hashlib
except ImportError:
    import md5 as hashlib

config = ConfigParser.ConfigParser({'testOutputBaseDir': '.',
                                    'smallSampleKey_nlmsa': ''})
config.read([os.path.join(os.path.expanduser('~'), '.pygrrc'),
             os.path.join(os.path.expanduser('~'), 'pygr.cfg'),
             '.pygrrc', 'pygr.cfg'])
mafDir = config.get('megatests_dm2', 'mafDir')
seqDir = config.get('megatests_dm2', 'seqDir')
smallSampleKey = config.get('megatests_dm2', 'smallSampleKey_nlmsa')
testInputDir = config.get('megatests', 'testInputDir')
testOutputBaseDir = config.get('megatests', 'testOutputBaseDir')

if smallSampleKey:
    smallSamplePostfix = '_' + smallSampleKey
else:
    smallSamplePostfix = ''

## mafDir CONTAINS FOLLOWING DM2 MULTIZ15WAY MAF ALIGNMENTS
## seqDir CONTAINS FOLLOWING 15 GENOME ASSEMBLIES AND THEIR SEQDB FILES
## TEST INPUT/OUPTUT FOR COMPARISON, THESE FILES SHOULD BE IN THIS DIRECTORY
##        outfileName = 'splicesite_dm2.txt' # CHR4H TESTING
##        outputName = 'splicesite_dm2_multiz15way.txt' # CHR4H TESTING
## testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList)) SHOULD
## BE DELETED IF YOU WANT TO RUN IN '.'

# DIRECTIONARY FOR DOC STRING OF SEQDB
docStringDict = {
    'anoGam1': 'A. gambiae Genome (February 2003)',
    'apiMel2': 'A. mellifera Genome (January 2005)',
    'dm2': 'D. melanogaster Genome (April 2004)',
    'dp4': 'D. pseudoobscura Genome (February 2006)',
    'droAna3': 'D. ananassae Genome (February 2006)',
    'droEre2': 'D. erecta Genome (February 2006)',
    'droGri2': 'D. grimshawi Genome (February 2006)',
    'droMoj3': 'D. mojavensis Genome (February 2006)',
    'droPer1': 'D. persimilis Genome (October 2005)',
    'droSec1': 'D. sechellia Genome (October 2005)',
    'droSim1': 'D. simulans Genome (April 2005)',
    'droVir3': 'D. virilis Genome (February 2006)',
    'droWil1': 'D. willistoni Genome (February 2006)',
    'droYak2': 'D. yakuba Genome (November 2005)',
    'triCas2': 'T. castaneum Genome (September 2005)',
    }

# GENOME ASSEMBLY LIST FOR DM2 MULTIZ15WAY
msaSpeciesList = ['anoGam1', 'apiMel2', 'dm2', 'dp4', 'droAna3', 'droEre2',
                  'droGri2', 'droMoj3', 'droPer1', 'droSec1', 'droSim1',
                  'droVir3', 'droWil1', 'droYak2', 'triCas2']


class PygrBuildNLMSAMegabase(unittest.TestCase):

    def setUp(self, testDir=None):
        '''restrict megatest to an initially empty directory, need
        large space to perform'''
        import random
        tmpList = [c for c in 'PygrBuildNLMSAMegabase']
        random.shuffle(tmpList)
        # Comment out the next line to run in current directory.
        testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList))
        if testDir is None:
            testDir = 'TEST_' + ''.join(tmpList)
        try:
            os.mkdir(testDir)
            testDir = os.path.realpath(testDir)
        except:
            raise IOError
        self.path = testDir
        try:
            tmpFileName = os.path.join(testDir, 'DELETE_THIS_TEMP_FILE')
            open(tmpFileName, 'w').write('A' * 1024 * 1024)
        except:
            raise IOError
        pygr.Data.update(self.path)
        from pygr import seqdb
        for orgstr in msaSpeciesList:
            genome = seqdb.BlastDB(os.path.join(seqDir, orgstr))
            genome.__doc__ = docStringDict[orgstr]
            pygr.Data.addResource('TEST.Seq.Genome.' + orgstr, genome)
        pygr.Data.save()

    def copyFile(self, filename): # COPY A FILE INTO TEST DIRECTORY
        newname = os.path.join(self.path, os.path.basename(filename))
        open(newname, 'w').write(open(filename, 'r').read())
        return newname

    def tearDown(self):
        'delete the temporary directory and files, restore pygr.Data path'
        # Delete them bottom-up for obvious reasons.
        for dirpath, subdirs, files in os.walk(self.path, topdown=False):
            # Note: this part may not work in directories on NFS due to
            # creation of lock files (.nfsXXXXXXXXX), which will only allow
            # deletion after pygr.Data has been closed.
            for filename in files:
                os.remove(os.path.join(dirpath, filename))
            os.rmdir(dirpath)
        # Restore original pygr.Data path to remedy lack of isolation
        # between tests from the same run
        pygr.Data.update(None)


class Build_Test(PygrBuildNLMSAMegabase):

    def test_seqdb(self):
        'Check pygr.Data contents'
        l = pygr.Data.dir('TEST')
        preList = ['TEST.Seq.Genome.' + orgstr for orgstr in msaSpeciesList]
        assert l == preList

    def test_build(self):
        'Test building an NLMSA and querying results'
        from pygr import seqdb, cnestedlist
        genomedict = {}
        for orgstr in msaSpeciesList:
            genomedict[orgstr] = pygr.Data.getResource('TEST.Seq.Genome.'
                                                       + orgstr)
        uniondict = seqdb.PrefixUnionDict(genomedict)
        if smallSampleKey:
            maflist = (os.path.join(mafDir, smallSampleKey + '.maf'), )
        else:
            maflist = glob.glob(os.path.join(mafDir, '*.maf'))
            maflist.sort()
        msaname = os.path.join(self.path, 'dm2_multiz15way')
        # 500MB VERSION
        msa1 = cnestedlist.NLMSA(msaname, 'w', uniondict, maflist,
                                 maxlen=536870912, maxint=22369620)
        msa1.__doc__ = 'TEST NLMSA for dm2 multiz15way'
        pygr.Data.addResource('TEST.MSA.UCSC.dm2_multiz15way', msa1)
        pygr.Data.save()
        msa = pygr.Data.getResource('TEST.MSA.UCSC.dm2_multiz15way')
        outfileName = os.path.join(testInputDir, 'splicesite_dm2%s.txt'
                                   % smallSamplePostfix)
        outputName = os.path.join(testInputDir,
                                  'splicesite_dm2%s_multiz15way.txt'
                                  % smallSamplePostfix)
        newOutputName = os.path.join(self.path, 'splicesite_new1.txt')
        tmpInputName = self.copyFile(outfileName)
        tmpOutputName = self.copyFile(outputName)
        outfile = open(newOutputName, 'w')
        for lines in open(tmpInputName, 'r').xreadlines():
            chrid, intstart, intend, nobs = string.split(lines.strip(), '\t')
            intstart, intend, nobs = int(intstart), int(intend), int(nobs)
            site1 = msa.seqDict['dm2' + '.' + chrid][intstart:intstart + 2]
            site2 = msa.seqDict['dm2' + '.' + chrid][intend - 2:intend]
            edges1 = msa[site1].edges()
            edges2 = msa[site2].edges()
            if len(edges1) == 0: # EMPTY EDGES
                wlist = str(site1), 'dm2', chrid, intstart, intstart + 2, \
                        '', '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            if len(edges2) == 0: # EMPTY EDGES
                wlist = str(site2), 'dm2', chrid, intend - 2, intend, '', \
                        '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            saveList = []
            for src, dest, e in edges1:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            for src, dest, e in edges2:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            saveList.sort() # SORTED IN ORDER TO COMPARE WITH PREVIOUS RESULTS
            for saveline in saveList:
                outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(newOutputName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(tmpOutputName, 'r').read())
        assert md5old.digest() == md5new.digest()

        # TEXT<->BINARY TEST
        msafilelist = glob.glob(msaname + '*')
        msa.save_seq_dict()
        cnestedlist.dump_textfile(msaname, os.path.join(self.path,
                                                       'dm2_multiz15way.txt'))
        for filename in msafilelist:
            os.remove(filename)
        runPath = os.path.realpath(os.curdir)
        os.chdir(self.path)
        cnestedlist.textfile_to_binaries('dm2_multiz15way.txt')
        os.chdir(runPath)

        msa1 = cnestedlist.NLMSA(msaname, 'r')
        msa1.__doc__ = 'TEST NLMSA for dm2 multiz15way'
        pygr.Data.addResource('TEST.MSA.UCSC.dm2_multiz15way', msa1)
        pygr.Data.save()
        msa = pygr.Data.getResource('TEST.MSA.UCSC.dm2_multiz15way')
        newOutputName = os.path.join(self.path, 'splicesite_new2.txt')
        tmpInputName = self.copyFile(outfileName)
        tmpOutputName = self.copyFile(outputName)
        outfile = open(newOutputName, 'w')
        for lines in open(tmpInputName, 'r').xreadlines():
            chrid, intstart, intend, nobs = string.split(lines.strip(), '\t')
            intstart, intend, nobs = int(intstart), int(intend), int(nobs)
            site1 = msa.seqDict['dm2' + '.' + chrid][intstart:intstart + 2]
            site2 = msa.seqDict['dm2' + '.' + chrid][intend - 2:intend]
            edges1 = msa[site1].edges()
            edges2 = msa[site2].edges()
            if len(edges1) == 0: # EMPTY EDGES
                wlist = str(site1), 'dm2', chrid, intstart, intstart + 2, \
                        '', '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            if len(edges2) == 0: # EMPTY EDGES
                wlist = str(site2), 'dm2', chrid, intend - 2, intend, '', \
                        '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            saveList = []
            for src, dest, e in edges1:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            for src, dest, e in edges2:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            saveList.sort() # SORTED IN ORDER TO COMPARE WITH PREVIOUS RESULTS
            for saveline in saveList:
                outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(newOutputName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(tmpOutputName, 'r').read())
        assert md5old.digest() == md5new.digest()


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = nlmsa_hg18_megatest
import unittest
from testlib import testutil, PygrTestProgram

import ConfigParser
import glob
import os
import string
import sys

import pygr.Data

try:
    import hashlib
except ImportError:
    import md5 as hashlib

config = ConfigParser.ConfigParser({'testOutputBaseDir': '.',
                                    'smallSampleKey': ''})
config.read([os.path.join(os.path.expanduser('~'), '.pygrrc'),
             os.path.join(os.path.expanduser('~'), 'pygr.cfg'),
             '.pygrrc', 'pygr.cfg'])
mafDir = config.get('megatests_hg18', 'mafDir')
seqDir = config.get('megatests_hg18', 'seqDir')
smallSampleKey = config.get('megatests_hg18', 'smallSampleKey')
testInputDir = config.get('megatests', 'testInputDir')
testOutputBaseDir = config.get('megatests', 'testOutputBaseDir')

if smallSampleKey:
    smallSamplePostfix = '_' + smallSampleKey
else:
    smallSamplePostfix = ''

## mafDir CONTAINS FOLLOWING DM2 MULTIZ15WAY MAF ALIGNMENTS
## seqDir CONTAINS FOLLOWING 15 GENOME ASSEMBLIES AND THEIR SEQDB FILES
## TEST INPUT/OUPTUT FOR COMPARISON, THESE FILES SHOULD BE IN THIS DIRECTORY
##        outfileName = 'splicesite_hg18.txt' # CHR4H TESTING
##        outputName = 'splicesite_hg18_multiz28way.txt' # CHR4H TESTING
## testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList)) SHOULD
## BE DELETED IF YOU WANT TO RUN IN '.'

# DIRECTIONARY FOR DOC STRING OF SEQDB
docStringDict = {
    'anoCar1': 'Lizard Genome (January 2007)',
    'bosTau3': 'Cow Genome (August 2006)',
    'canFam2': 'Dog Genome (May 2005)',
    'cavPor2': 'Guinea Pig (October 2005)',
    'danRer4': 'Zebrafish Genome (March 2006)',
    'dasNov1': 'Armadillo Genome (May 2005)',
    'echTel1': 'Tenrec Genome (July 2005)',
    'eriEur1': 'European Hedgehog (Junuary 2006)',
    'equCab1': 'Horse Genome (January 2007)',
    'felCat3': 'Cat Genome (March 2006)',
    'fr2': 'Fugu Genome (October 2004)',
    'galGal3': 'Chicken Genome (May 2006)',
    'gasAcu1': 'Stickleback Genome (February 2006)',
    'hg18': 'Human Genome (May 2006)',
    'loxAfr1': 'Elephant Genome (May 2005)',
    'mm8': 'Mouse Genome (March 2006)',
    'monDom4': 'Opossum Genome (January 2006)',
    'ornAna1': 'Platypus Genome (March 2007)',
    'oryCun1': 'Rabbit Genome (May 2005)',
    'oryLat1': 'Medaka Genome (April 2006)',
    'otoGar1': 'Bushbaby Genome (December 2006)',
    'panTro2': 'Chimpanzee Genome (March 2006)',
    'rheMac2': 'Rhesus Genome (January 2006)',
    'rn4': 'Rat Genome (November 2004)',
    'sorAra1': 'Shrew (Junuary 2006)',
    'tetNig1': 'Tetraodon Genome (February 2004)',
    'tupBel1': 'Tree Shrew (December 2006)',
    'xenTro2': 'X. tropicalis Genome (August 2005)',
    }

# GENOME ASSEMBLY LIST FOR DM2 MULTIZ15WAY
msaSpeciesList = ['anoCar1', 'bosTau3', 'canFam2', 'cavPor2', 'danRer4',
                  'dasNov1', 'echTel1', 'equCab1', 'eriEur1', 'felCat3', 'fr2',
                  'galGal3', 'gasAcu1', 'hg18', 'loxAfr1', 'mm8', 'monDom4',
                  'ornAna1', 'oryCun1', 'oryLat1', 'otoGar1', 'panTro2',
                  'rheMac2', 'rn4', 'sorAra1', 'tetNig1', 'tupBel1', 'xenTro2']


class PygrBuildNLMSAMegabase(unittest.TestCase):

    def setUp(self, testDir=None):
        '''restrict megatest to an initially empty directory, need
        large space to perform'''
        import random
        tmpList = [c for c in 'PygrBuildNLMSAMegabase']
        random.shuffle(tmpList)
        # Comment out the next line to run in current directory.
        testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList))
        if testDir is None:
            testDir = 'TEST_' + ''.join(tmpList)
        try:
            os.mkdir(testDir)
            testDir = os.path.realpath(testDir)
        except:
            raise IOError
        self.path = testDir
        try:
            tmpFileName = os.path.join(testDir, 'DELETE_THIS_TEMP_FILE')
            open(tmpFileName, 'w').write('A' * 1024 * 1024)
        except:
            raise IOError
        pygr.Data.update(self.path)
        from pygr import seqdb
        for orgstr in msaSpeciesList:
            genome = seqdb.BlastDB(os.path.join(seqDir, orgstr))
            genome.__doc__ = docStringDict[orgstr]
            pygr.Data.addResource('TEST.Seq.Genome.' + orgstr, genome)
        pygr.Data.save()

    def copyFile(self, filename): # COPY A FILE INTO TEST DIRECTORY
        newname = os.path.join(self.path, os.path.basename(filename))
        open(newname, 'w').write(open(filename, 'r').read())
        return newname

    def tearDown(self):
        'delete the temporary directory and files, restore pygr.Data path'
        # Delete them bottom-up for obvious reasons.
        for dirpath, subdirs, files in os.walk(self.path, topdown=False):
            # Note: this part may not work in directories on NFS due to
            # creation of lock files (.nfsXXXXXXXXX), which will only allow
            # deletion after pygr.Data has been closed.
            for filename in files:
                os.remove(os.path.join(dirpath, filename))
            os.rmdir(dirpath)
        # Restore original pygr.Data path to remedy lack of isolation
        # between tests from the same run
        pygr.Data.update(None)


class Build_Test(PygrBuildNLMSAMegabase):

    def test_seqdb(self):
        'Check pygr.Data contents'
        l = pygr.Data.dir('TEST')
        preList = ['TEST.Seq.Genome.' + orgstr for orgstr in msaSpeciesList]
        assert l == preList

    def test_build(self):
        'Test building an NLMSA and querying results'
        from pygr import seqdb, cnestedlist
        genomedict = {}
        for orgstr in msaSpeciesList:
            genomedict[orgstr] = pygr.Data.getResource('TEST.Seq.Genome.'
                                                       + orgstr)
        uniondict = seqdb.PrefixUnionDict(genomedict)
        if smallSampleKey:
            maflist = (os.path.join(mafDir, smallSampleKey + '.maf'), )
        else:
            maflist = glob.glob(os.path.join(mafDir, '*.maf'))
            maflist.sort()
        msaname = os.path.join(self.path, 'hg18_multiz28way')
        # 500MB VERSION
        msa1 = cnestedlist.NLMSA(msaname, 'w', uniondict, maflist,
                                 maxlen=536870912, maxint=22369620)
        msa1.__doc__ = 'TEST NLMSA for hg18 multiz28way'
        pygr.Data.addResource('TEST.MSA.UCSC.hg18_multiz28way', msa1)
        pygr.Data.save()
        msa = pygr.Data.getResource('TEST.MSA.UCSC.hg18_multiz28way')
        outfileName = os.path.join(testInputDir, 'splicesite_hg18%s.txt'
                                   % smallSamplePostfix)
        outputName = os.path.join(testInputDir,
                                  'splicesite_hg18%s_multiz28way.txt'
                                  % smallSamplePostfix)
        newOutputName = os.path.join(self.path, 'splicesite_new1.txt')
        tmpInputName = self.copyFile(outfileName)
        tmpOutputName = self.copyFile(outputName)
        outfile = open(newOutputName, 'w')
        for lines in open(tmpInputName, 'r').xreadlines():
            chrid, intstart, intend, nobs = string.split(lines.strip(), '\t')
            intstart, intend, nobs = int(intstart), int(intend), int(nobs)
            site1 = msa.seqDict['hg18' + '.' + chrid][intstart:intstart + 2]
            site2 = msa.seqDict['hg18' + '.' + chrid][intend - 2:intend]
            edges1 = msa[site1].edges()
            edges2 = msa[site2].edges()
            if len(edges1) == 0: # EMPTY EDGES
                wlist = str(site1), 'hg18', chrid, intstart, intstart + 2, \
                        '', '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            if len(edges2) == 0: # EMPTY EDGES
                wlist = str(site2), 'hg18', chrid, intend - 2, intend, '', \
                        '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            saveList = []
            for src, dest, e in edges1:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            for src, dest, e in edges2:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            saveList.sort() # SORTED IN ORDER TO COMPARE WITH PREVIOUS RESULTS
            for saveline in saveList:
                outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(newOutputName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(tmpOutputName, 'r').read())
        assert md5old.digest() == md5new.digest()

        # TEXT<->BINARY TEST
        msafilelist = glob.glob(msaname + '*')
        msa.save_seq_dict()
        cnestedlist.dump_textfile(msaname, os.path.join(self.path,
                                                       'hg18_multiz28way.txt'))
        for filename in msafilelist:
            os.remove(filename)
        runPath = os.path.realpath(os.curdir)
        os.chdir(self.path)
        cnestedlist.textfile_to_binaries('hg18_multiz28way.txt')
        os.chdir(runPath)

        msa1 = cnestedlist.NLMSA(msaname, 'r')
        msa1.__doc__ = 'TEST NLMSA for hg18 multiz28way'
        pygr.Data.addResource('TEST.MSA.UCSC.hg18_multiz28way', msa1)
        pygr.Data.save()
        msa = pygr.Data.getResource('TEST.MSA.UCSC.hg18_multiz28way')
        newOutputName = os.path.join(self.path, 'splicesite_new2.txt')
        tmpInputName = self.copyFile(outfileName)
        tmpOutputName = self.copyFile(outputName)
        outfile = open(newOutputName, 'w')
        for lines in open(tmpInputName, 'r').xreadlines():
            chrid, intstart, intend, nobs = string.split(lines.strip(), '\t')
            intstart, intend, nobs = int(intstart), int(intend), int(nobs)
            site1 = msa.seqDict['hg18' + '.' + chrid][intstart:intstart + 2]
            site2 = msa.seqDict['hg18' + '.' + chrid][intend - 2:intend]
            edges1 = msa[site1].edges()
            edges2 = msa[site2].edges()
            if len(edges1) == 0: # EMPTY EDGES
                wlist = str(site1), 'hg18', chrid, intstart, intstart + 2, \
                        '', '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            if len(edges2) == 0: # EMPTY EDGES
                wlist = str(site2), 'hg18', chrid, intend - 2, intend, '', \
                        '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            saveList = []
            for src, dest, e in edges1:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            for src, dest, e in edges2:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            saveList.sort() # SORTED IN ORDER TO COMPARE WITH PREVIOUS RESULTS
            for saveline in saveList:
                outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(newOutputName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(tmpOutputName, 'r').read())
        assert md5old.digest() == md5new.digest()


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = nlmsa_test
import unittest
from testlib import testutil, PygrTestProgram
from pygr import cnestedlist, nlmsa_utils, seqdb, sequence


class NestedList_Test(unittest.TestCase):
    "Basic cnestedlist class tests"

    def setUp(self):
        self.db = cnestedlist.IntervalDB()
        ivals = [(0, 10, 1, -110, -100), (-20, -5, 2, 300, 315)]
        self.db.save_tuples(ivals)

    def test_query(self):
        "NestedList query"
        assert self.db.find_overlap_list(0, 10) == \
                         [(0, 10, 1, -110, -100), (5, 20, 2, -315, -300)]

    def test_reverse(self):
        "NestedList reverse"
        assert self.db.find_overlap_list(-11, -7) == \
                         [(-10, 0, 1, 100, 110), (-20, -5, 2, 300, 315)]

    def test_filedb(self):
        "NestedList filedb"
        tempdir = testutil.TempDir('nlmsa-test')
        filename = tempdir.subfile('nlmsa')
        self.db.write_binaries(filename)
        fdb = cnestedlist.IntervalFileDB(filename)
        assert fdb.find_overlap_list(0, 10) == \
                         [(0, 10, 1, -110, -100), (5, 20, 2, -315, -300)]
        assert fdb.find_overlap_list(-11, -7) == \
                         [(-10, 0, 1, 100, 110), (-20, -5, 2, 300, 315)]

        # fails on windows
        #tempdir.remove()  @CTB


class NLMSA_SimpleTests(unittest.TestCase):

    def setUp(self):
        pass

    def test_empty(self):
        "NLMSA Empty"
        blasthits = testutil.tempdatafile('blasthits')

        msa = cnestedlist.NLMSA(blasthits, 'memory', pairwiseMode=True)
        try:
            msa.build()
            raise AssertionError('failed to trap empty alignment!')
        except nlmsa_utils.EmptyAlignmentError:
            pass

    def test_empty2(self):
        "NLMSA Empty 2"
        blasthits = testutil.tempdatafile('blasthits2')
        msa = cnestedlist.NLMSA(blasthits, mode='w', pairwiseMode=True)
        try:
            msa.build()
            raise AssertionError('failed to trap empty alignment!')
        except nlmsa_utils.EmptyAlignmentError:
            pass

    def test_build(self):
        "NLMSA build"

        testnlmsa = testutil.tempdatafile('testnlmsa')
        msa = cnestedlist.NLMSA(testnlmsa, mode='w', pairwiseMode=True,
                                bidirectional=False)
        # @CTB should there be something else here?  What is this testing?

    def test_lpo_query(self):
        s1=sequence.Sequence('aaaa', 's1')
        s2=sequence.Sequence('bbbb', 's2')
        msa = cnestedlist.NLMSA(mode='memory')
        msa[0:4] += s1
        msa[0:4] += s2
        msa.build()
        msaSlice = msa[0:4]
        assert len(msaSlice) == 2
        l = [t[0:2] for t in msaSlice.edges()]
        l.sort()
        correct = [(slice(0, 4), s1), (slice(0, 4), s2)]
        correct.sort()
        assert l == correct


class NLMSA_Test(unittest.TestCase):

    def setUp(self):
        s = sequence.Sequence('ATGGACAGAGATGACAGATGAC', 'a')
        s2 = sequence.Sequence('ATGGGAGCAGCATGACAGATGAC', 'b')

        # make a non-empty NLMSA
        nlmsa = cnestedlist.NLMSA('foo', mode='memory', pairwiseMode=True)
        nlmsa += s
        nlmsa[s] += s2
        nlmsa.build()

        self.s = s
        self.s2 = s2
        self.nlmsa = nlmsa

    def test_iter(self):
        "Iteration of NLMSA objects should return reasonable error."

        # try iterating over it
        try:
            for x in self.nlmsa:
                break                   # should fail before this

            assert 0, "should not be able to iterate over NLMSA"
        except NotImplementedError:
            pass

    def test_slice_repr(self):
        "Ask for an informative __repr__ on NLMSASlice objects"

        slice = self.nlmsa[self.s]
        r = repr(slice)
        assert 'seq=a' in r

        slice = self.nlmsa[self.s2]
        r = repr(slice)
        assert 'seq=b' in r


class NLMSA_BuildWithAlignedIntervals_Test(unittest.TestCase):

    def setUp(self):
        seqdb_name = testutil.datafile('alignments.fa')
        self.db = seqdb.SequenceFileDB(seqdb_name)

    def _check_results(self, n):
        db = self.db

        a, b, c = db['a'], db['b'], db['c']

        ival = a[0:8]
        (result, ) = n[ival].keys()
        assert result == b[0:8]

        ival = a[12:20]
        (result, ) = n[ival].keys()
        assert result == c[0:8]

        l = list(n[a].keys())
        l.sort()
        assert b[0:8] in l
        assert c[0:8] in l

    def test_simple(self):
        # first set of intervals
        ivals = [(('a', 0, 8, 1), ('b', 0, 8, 1), ),
                 (('a', 12, 20, 1), ('c', 0, 8, 1)), ]

        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True)

        alignedIvalsAttrs = dict(id=0, start=1, stop=2, idDest=0, startDest=1,
                                 stopDest=2, ori=3, oriDest=3)
        cti = nlmsa_utils.CoordsToIntervals(self.db, self.db,
                                            alignedIvalsAttrs)
        n.add_aligned_intervals(cti(ivals))
        n.build()

        self._check_results(n)

    def test_simple_no_ori(self):
        # first set of intervals
        ivals = [(('a', 0, 8, ), ('b', 0, 8, ), ),
                 (('a', 12, 20, ), ('c', 0, 8, )), ]

        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True)

        alignedIvalsAttrs = dict(id=0, start=1, stop=2, idDest=0, startDest=1,
                                 stopDest=2)
        cti = nlmsa_utils.CoordsToIntervals(self.db, self.db,
                                            alignedIvalsAttrs)
        n.add_aligned_intervals(cti(ivals))
        n.build()

        self._check_results(n)

    def test_attr(self):

        class Bag(object):

            def __init__(self, **kw):
                self.__dict__.update(kw)

        # first set of intervals
        db = self.db
        a, b, c = db['a'], db['b'], db['c']

        src_ival1 = Bag(id='a', start=0, stop=8, ori=1)
        dst_ival1 = Bag(id='b', start=0, stop=8, ori=1)

        src_ival2 = Bag(id='a', start=12, stop=20, ori=1)
        dst_ival2 = Bag(id='c', start=0, stop=8, ori=1)

        ivals = [(src_ival1, dst_ival1), (src_ival2, dst_ival2)]

        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True)

        cti = nlmsa_utils.CoordsToIntervals(self.db, self.db)
        n.add_aligned_intervals(cti(ivals))
        n.build()

        self._check_results(n)

    def test_single_ival_attr(self):

        class Bag(object):

            def __init__(self, **kw):
                self.__dict__.update(kw)

        # first set of intervals
        db = self.db
        a, b, c = db['a'], db['b'], db['c']

        ival1 = Bag(id='a', start=0, stop=8, ori=1,
                    idDest='b', startDest=0, stopDest=8, stopOri=1)
        ival2 = Bag(id='a', start=12, stop=20, ori=1,
                    idDest='c', startDest=0, stopDest=8, oriDest=1)

        ivals = [ival1, ival2]

        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True)

        cti = nlmsa_utils.CoordsToIntervals(self.db, self.db, {})
        n.add_aligned_intervals(cti(ivals))
        n.build()

        self._check_results(n)

    def test_no_seqDict_args(self):

        class Bag(object):

            def __init__(self, **kw):
                self.__dict__.update(kw)

        # first set of intervals
        db = self.db

        src_ival1 = Bag(id='a', start=0, stop=8, ori=1)
        dst_ival1 = Bag(id='b', start=0, stop=8, ori=1)

        src_ival2 = Bag(id='a', start=12, stop=20, ori=1)
        dst_ival2 = Bag(id='c', start=0, stop=8, ori=1)

        ivals = [(src_ival1, dst_ival1), (src_ival2, dst_ival2)]

        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              seqDict=db)

        cti = nlmsa_utils.CoordsToIntervals(self.db)
        n.add_aligned_intervals(cti(ivals))
        n.build()

class NLMSASeqDict_Test(unittest.TestCase):

    def setUp(self):
        seqdb_name = testutil.datafile('alignments.fa')
        self.db = seqdb.SequenceFileDB(seqdb_name)

    def _add_seqs(self, n):
        # CTB: note, force hard references for weakref checking behavior
        self.a = a = self.db['a']
        self.b = b = self.db['b']
        self.c = c = self.db['c']

        pairs = ((a[0:8], b[0:8]),
                 (a[12:20], c[0:8]))
        
        n += a
        for src, dest in pairs:
            n[src] += dest

    def test_cache_size0(self):
        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              maxSequenceCacheSize=0)
        self._add_seqs(n)

        # should be zero elements: cachesize of 0
        assert len(n.seqs._cache) == 0
        
    def test_cache_size1(self):
        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              maxSequenceCacheSize=1)
        self._add_seqs(n)

        # should be 1 elements: cachesize of 1
        assert len(n.seqs._cache) == 1

    def test_cache_size1(self):
        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              maxSequenceCacheSize=1)
        self._add_seqs(n)

        # should be 1 element: cachesize of 1
        assert len(n.seqs._cache) == 1

    def test_cache_size2(self):
        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              maxSequenceCacheSize=2)
        self._add_seqs(n)

        # should be 2 elements: cachesize of 2
        assert len(n.seqs._cache) == 2

    def test_cache_size4(self):
        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              maxSequenceCacheSize=4)
        self._add_seqs(n)

        # should be 3 elements: cachesize of 4, but only three sequences
        assert len(n.seqs._cache) == 3, len(n.seqs._cache)
        
    def test_clear_cache(self):
        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              maxSequenceCacheSize=4)
        self._add_seqs(n)

        # should be 3 elements: cachesize of 4, but only three sequences
        assert len(n.seqs._cache) == 3, len(n.seqs._cache)

        # now clear the cache
        n.seqs.clear_cache()
        assert len(n.seqs._cache) == 0, len(n.seqs._cache)

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = pairwise_hg18_megatest
import unittest
from testlib import testutil, PygrTestProgram

import ConfigParser
import glob
import os
import string
import sys

import pygr.Data

try:
    import hashlib
except ImportError:
    import md5 as hashlib

config = ConfigParser.ConfigParser({'testOutputBaseDir': '.',
                                    'smallSampleKey': ''})
config.read([os.path.join(os.path.expanduser('~'), '.pygrrc'),
             os.path.join(os.path.expanduser('~'), 'pygr.cfg'),
             '.pygrrc', 'pygr.cfg'])
axtDir = config.get('megatests_hg18', 'axtDir')
seqDir = config.get('megatests_hg18', 'seqDir')
smallSampleKey = config.get('megatests_hg18', 'smallSampleKey')
testInputDir = config.get('megatests', 'testInputDir')
testOutputBaseDir = config.get('megatests', 'testOutputBaseDir')

if smallSampleKey:
    smallSamplePostfix = '_' + smallSampleKey
else:
    smallSamplePostfix = ''

## axtDir CONTAINS: hg18_canFam2  hg18_mm8  hg18_panTro2  hg18_rn4  hg18_self
## seqDir CONTAINS FOLLOWING 15 GENOME ASSEMBLIES AND THEIR SEQDB FILES
## TEST INPUT/OUPTUT FOR COMPARISON, THESE FILES SHOULD BE IN THIS DIRECTORY
##        outfileName = 'splicesite_hg18.txt' # CHR4H TESTING
##        outputName = 'splicesite_hg18_pairwise5way.txt' # CHR4H TESTING
## testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList)) SHOULD
## BE DELETED IF YOU WANT TO RUN IN '.'

# DIRECTIONARY FOR DOC STRING OF SEQDB
docStringDict = {
    'canFam2': 'Dog Genome (May 2005)',
    'hg18': 'Human Genome (May 2006)',
    'mm8': 'Mouse Genome (March 2006)',
    'panTro2': 'Chimpanzee Genome (March 2006)',
    'rn4': 'Rat Genome (November 2004)',
    }

# GENOME ASSEMBLY LIST FOR DM2 MULTIZ15WAY
msaSpeciesList = ['canFam2', 'hg18', 'mm8', 'panTro2', 'rn4']


class PygrBuildNLMSAMegabase(unittest.TestCase):

    def setUp(self, testDir=None):
        '''restrict megatest to an initially empty directory, need
        large space to perform'''
        import random
        tmpList = [c for c in 'PygrBuildNLMSAMegabase']
        random.shuffle(tmpList)
        # Comment out the next line to run in current directory.
        testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList))
        if testDir is None:
            testDir = 'TEST_' + ''.join(tmpList)
        try:
            os.mkdir(testDir)
            testDir = os.path.realpath(testDir)
        except:
            raise IOError
        self.path = testDir
        try:
            tmpFileName = os.path.join(testDir, 'DELETE_THIS_TEMP_FILE')
            open(tmpFileName, 'w').write('A' * 1024 * 1024)
        except:
            raise IOError
        pygr.Data.update(self.path)
        from pygr import seqdb
        for orgstr in msaSpeciesList:
            genome = seqdb.BlastDB(os.path.join(seqDir, orgstr))
            genome.__doc__ = docStringDict[orgstr]
            pygr.Data.addResource('TEST.Seq.Genome.' + orgstr, genome)
        pygr.Data.save()

    def copyFile(self, filename): # COPY A FILE INTO TEST DIRECTORY
        newname = os.path.join(self.path, os.path.basename(filename))
        open(newname, 'w').write(open(filename, 'r').read())
        return newname

    def tearDown(self):
        'delete the temporary directory and files, restore pygr.Data path'
        # Delete them bottom-up for obvious reasons.
        for dirpath, subdirs, files in os.walk(self.path, topdown=False):
            # Note: this part may not work in directories on NFS due to
            # creation of lock files (.nfsXXXXXXXXX), which will only allow
            # deletion after pygr.Data has been closed.
            for filename in files:
                os.remove(os.path.join(dirpath, filename))
            os.rmdir(dirpath)
        # Restore original pygr.Data path to remedy lack of isolation
        # between tests from the same run
        pygr.Data.update(None)


class Build_Test(PygrBuildNLMSAMegabase):

    def test_seqdb(self):
        'Check pygr.Data contents'
        l = pygr.Data.dir('TEST')
        preList = ['TEST.Seq.Genome.' + orgstr for orgstr in msaSpeciesList]
        assert l == preList

    def test_build(self):
        'Test building an NLMSA and querying results'
        from pygr import seqdb, cnestedlist
        genomedict = {}
        for orgstr in msaSpeciesList:
            genomedict[orgstr] = pygr.Data.getResource('TEST.Seq.Genome.'
                                                       + orgstr)
        uniondict = seqdb.PrefixUnionDict(genomedict)
        if smallSampleKey:
            axtlist = glob.glob(os.path.join(axtDir, '*' + os.sep
                                             + smallSampleKey + '.*.net.axt'))
        else:
            axtlist = glob.glob(os.path.join(axtDir, '*' + os.sep
                                             + '*.*.net.axt'))
        axtlist.sort()
        msaname = os.path.join(self.path, 'hg18_pairwise5way')
        # 500MB VERSION
        msa1 = cnestedlist.NLMSA(msaname, 'w', uniondict, axtFiles=axtlist,
                                 maxlen=536870912, maxint=22369620)
        msa1.__doc__ = 'TEST NLMSA for hg18 pairwise5way'
        pygr.Data.addResource('TEST.MSA.UCSC.hg18_pairwise5way', msa1)
        pygr.Data.save()
        msa = pygr.Data.getResource('TEST.MSA.UCSC.hg18_pairwise5way')
        outfileName = os.path.join(testInputDir, 'splicesite_hg18%s.txt'
                                   % smallSamplePostfix)
        outputName = os.path.join(testInputDir,
                                  'splicesite_hg18%s_pairwise5way.txt'
                                  % smallSamplePostfix)
        newOutputName = 'splicesite_new1.txt'
        tmpInputName = self.copyFile(outfileName)
        tmpOutputName = self.copyFile(outputName)
        tmpNewOutputName = os.path.join(self.path, newOutputName)
        outfile = open(tmpNewOutputName, 'w')
        for lines in open(tmpInputName, 'r').xreadlines():
            chrid, intstart, intend, nobs = string.split(lines.strip(), '\t')
            intstart, intend, nobs = int(intstart), int(intend), int(nobs)
            site1 = msa.seqDict['hg18' + '.' + chrid][intstart:intstart + 2]
            site2 = msa.seqDict['hg18' + '.' + chrid][intend - 2:intend]
            edges1 = msa[site1].edges()
            edges2 = msa[site2].edges()
            if len(edges1) == 0: # EMPTY EDGES
                wlist = str(site1), 'hg18', chrid, intstart, intstart + 2, \
                        '', '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            if len(edges2) == 0: # EMPTY EDGES
                wlist = str(site2), 'hg18', chrid, intend - 2, intend, '', \
                        '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            saveList = []
            for src, dest, e in edges1:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            for src, dest, e in edges2:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            saveList.sort() # SORTED IN ORDER TO COMPARE WITH PREVIOUS RESULTS
            for saveline in saveList:
                outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpNewOutputName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(tmpOutputName, 'r').read())
        assert md5old.digest() == md5new.digest()

        # TEXT<->BINARY TEST
        msafilelist = glob.glob(msaname + '*')
        msa.save_seq_dict()
        cnestedlist.dump_textfile(msaname, os.path.join(self.path,
                                                      'hg18_pairwise5way.txt'))
        for filename in msafilelist:
            os.remove(filename)
        runPath = os.path.realpath(os.curdir)
        os.chdir(self.path)
        cnestedlist.textfile_to_binaries('hg18_pairwise5way.txt')
        os.chdir(runPath)

        msa1 = cnestedlist.NLMSA(msaname, 'r')
        msa1.__doc__ = 'TEST NLMSA for hg18 pairwise5way'
        pygr.Data.addResource('TEST.MSA.UCSC.hg18_pairwise5way', msa1)
        pygr.Data.save()
        msa = pygr.Data.getResource('TEST.MSA.UCSC.hg18_pairwise5way')
        newOutputName = 'splicesite_new2.txt'
        tmpInputName = self.copyFile(outfileName)
        tmpOutputName = self.copyFile(outputName)
        tmpNewOutputName = os.path.join(self.path, newOutputName)
        outfile = open(tmpNewOutputName, 'w')
        for lines in open(tmpInputName, 'r').xreadlines():
            chrid, intstart, intend, nobs = string.split(lines.strip(), '\t')
            intstart, intend, nobs = int(intstart), int(intend), int(nobs)
            site1 = msa.seqDict['hg18' + '.' + chrid][intstart:intstart + 2]
            site2 = msa.seqDict['hg18' + '.' + chrid][intend - 2:intend]
            edges1 = msa[site1].edges()
            edges2 = msa[site2].edges()
            if len(edges1) == 0: # EMPTY EDGES
                wlist = str(site1), 'hg18', chrid, intstart, intstart + 2, \
                        '', '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            if len(edges2) == 0: # EMPTY EDGES
                wlist = str(site2), 'hg18', chrid, intend - 2, intend, '', \
                        '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            saveList = []
            for src, dest, e in edges1:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            for src, dest, e in edges2:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            saveList.sort() # SORTED IN ORDER TO COMPARE WITH PREVIOUS RESULTS
            for saveline in saveList:
                outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpNewOutputName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(tmpOutputName, 'r').read())
        assert md5old.digest() == md5new.digest()


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = pygrdata_test
import datetime
import md5
import os
import pickle
import socket
import unittest
import warnings

import testlib
from testlib import testutil, SkipTest, PygrTestProgram
from pygr import seqdb, cnestedlist, mapping
from pygr.downloader import SourceURL, GenericBuilder


warnings.simplefilter("ignore")
import pygr.Data
warnings.simplefilter("default")

try:
    set
except NameError:
    from sets import Set as set


class TestBase(unittest.TestCase):
    "A base class to all pygr.Data test classes"

    def setUp(self, pygrDataPath=None, **kwargs):
        # overwrite the WORLDBASEPATH environment variable
        self.tempdir = testutil.TempDir('pygrdata')
        if pygrDataPath is None:
            pygrDataPath = self.tempdir.path
        pygr.Data.clear_cache() # make sure no old data loaded
        pygr.Data.update(pygrDataPath, **kwargs) # use this path
        # handy shortcuts
        self.EQ = self.assertEqual


class Download_Test(TestBase):
    "Save seq db and interval to pygr.Data shelve"

    # tested elsewhere as well, on Linux makes gzip ask for permissions
    # to overwrite
    def test_download(self):
        "Downloading of gzipped file using pygr.Data"

        url = SourceURL('http://www.doe-mbi.ucla.edu/~leec/test.gz')
        url.__doc__ = 'test download'

        pygr.Data.addResource('Bio.Test.Download1', url)
        pygr.Data.save()

        # performs the download
        fpath = pygr.Data.Bio.Test.Download1()
        h = testutil.get_file_md5(fpath)
        self.assertEqual(h.hexdigest(), 'f95656496c5182d6cff9a56153c9db73')
        os.remove(fpath)


class GenericBuild_Test(TestBase):

    def test_generic_build(self):
        "GenericBuilder construction of the BlastDB"

        sp_hbb1 = testutil.datafile('sp_hbb1')
        gb = GenericBuilder('BlastDB', sp_hbb1)
        s = pickle.dumps(gb)
        db = pickle.loads(s) # force construction of the BlastDB
        self.EQ(len(db), 24)

        found = [x for x in db]
        found.sort()

        expected = ['HBB0_PAGBO', 'HBB1_ANAMI', 'HBB1_CYGMA', 'HBB1_IGUIG',
                   'HBB1_MOUSE', 'HBB1_ONCMY', 'HBB1_PAGBO', 'HBB1_RAT',
                   'HBB1_SPHPU', 'HBB1_TAPTE', 'HBB1_TORMA', 'HBB1_TRICR',
                   'HBB1_UROHA', 'HBB1_VAREX', 'HBB1_XENBO', 'HBB1_XENLA',
                   'HBB1_XENTR', 'MYG_DIDMA', 'MYG_ELEMA', 'MYG_ERIEU',
                   'MYG_ESCGI', 'MYG_GALCR', 'PRCA_ANASP', 'PRCA_ANAVA']
        expected.sort()

        self.EQ(expected, found)


class DNAAnnotation_Test(TestBase):

    def setUp(self, **kwargs):
        TestBase.setUp(self)
        dnaseq = testutil.datafile('dnaseq.fasta')
        tryannot = testutil.tempdatafile('tryannot')

        db = seqdb.BlastDB(dnaseq)
        try:
            db.__doc__ = 'little dna'

            pygr.Data.Bio.Test.dna = db
            annoDB = seqdb.AnnotationDB({1: ('seq1', 5, 10, 'fred'),
                                         2: ('seq1', -60, -50, 'bob'),
                                         3: ('seq2', -20, -10, 'mary')},
                                        db,
                                  sliceAttrDict=dict(id=0, start=1, stop=2,
                                                     name=3))
            annoDB.__doc__ = 'trivial annotation'
            pygr.Data.Bio.Test.annoDB = annoDB
            nlmsa = cnestedlist.NLMSA(tryannot, 'w', pairwiseMode=True,
                                      bidirectional=False)
            try:
                for annID in annoDB:
                    nlmsa.addAnnotation(annoDB[annID])

                nlmsa.build()
                nlmsa.__doc__ = 'trivial map'
                pygr.Data.Bio.Test.map = nlmsa
                pygr.Data.schema.Bio.Test.map = \
                       pygr.Data.ManyToManyRelation(db, annoDB,
                                                    bindAttrs=('exons', ))
                pygr.Data.save()
                pygr.Data.clear_cache()
            finally:
                nlmsa.close()
        finally:
            db.close()

    def test_annotation(self):
        "Annotation test"
        db = pygr.Data.Bio.Test.dna()
        try:
            s1 = db['seq1']
            l = s1.exons.keys()
            annoDB = pygr.Data.Bio.Test.annoDB()
            assert l == [annoDB[1], -(annoDB[2])]
            assert l[0].sequence == s1[5:10]
            assert l[1].sequence == s1[50:60]
            assert l[0].name == 'fred', 'test annotation attribute access'
            assert l[1].name == 'bob'
            sneg = -(s1[:55])
            l = sneg.exons.keys()
            assert l == [annoDB[2][5:], -(annoDB[1])]
            assert l[0].sequence == -(s1[50:55])
            assert l[1].sequence == -(s1[5:10])
            assert l[0].name == 'bob'
            assert l[1].name == 'fred'
        finally:
            db.close() # close SequenceFileDB
            pygr.Data.Bio.Test.map().close() # close NLMSA


def populate_swissprot():
    "Populate the current pygrData with swissprot data"
    # build BlastDB out of the sequences
    sp_hbb1 = testutil.datafile('sp_hbb1')
    sp = seqdb.BlastDB(sp_hbb1)
    sp.__doc__ = 'little swissprot'
    pygr.Data.Bio.Seq.Swissprot.sp42 = sp

    # also store a fragment
    hbb = sp['HBB1_TORMA']
    ival= hbb[10:35]
    ival.__doc__ = 'fragment'
    pygr.Data.Bio.Seq.frag = ival

    # build a mapping to itself
    m = mapping.Mapping(sourceDB=sp, targetDB=sp)
    trypsin = sp['PRCA_ANAVA']
    m[hbb] = trypsin
    m.__doc__ = 'map sp to itself'
    pygr.Data.Bio.Seq.spmap = m

    # create an annotation database and bind as exons attribute
    pygr.Data.schema.Bio.Seq.spmap = \
           pygr.Data.OneToManyRelation(sp, sp, bindAttrs=('buddy', ))
    annoDB = seqdb.AnnotationDB({1: ('HBB1_TORMA', 10, 50)}, sp,
                                sliceAttrDict=dict(id=0, start=1, stop=2))
    exon = annoDB[1]

    # generate the names where these will be stored
    tempdir = testutil.TempDir('exonAnnot')
    filename = tempdir.subfile('cnested')
    nlmsa = cnestedlist.NLMSA(filename, 'w', pairwiseMode=True,
                              bidirectional=False)
    nlmsa.addAnnotation(exon)
    nlmsa.build()
    annoDB.__doc__ = 'a little annotation db'
    nlmsa.__doc__ = 'a little map'
    pygr.Data.Bio.Annotation.annoDB = annoDB
    pygr.Data.Bio.Annotation.map = nlmsa
    pygr.Data.schema.Bio.Annotation.map = \
         pygr.Data.ManyToManyRelation(sp, annoDB, bindAttrs=('exons', ))


def check_match(self):
    frag = pygr.Data.Bio.Seq.frag()
    correct = pygr.Data.Bio.Seq.Swissprot.sp42()['HBB1_TORMA'][10:35]
    assert frag == correct, 'seq ival should match'
    assert frag.__doc__ == 'fragment', 'docstring should match'
    assert str(frag) == 'IQHIWSNVNVVEITAKALERVFYVY', 'letters should match'
    assert len(frag) == 25, 'length should match'
    assert len(frag.path) == 142, 'length should match'

    #store = PygrDataTextFile('results/seqdb1.pickle')
    #saved = store['hbb1 fragment']
    #assert frag == saved, 'seq ival should matched stored result'


def check_dir(self):
    expected=['Bio.Annotation.annoDB', 'Bio.Annotation.map',
                'Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap']
    expected.sort()
    found = pygr.Data.dir('Bio')
    found.sort()
    assert found == expected


def check_dir_noargs(self):
    found = pygr.Data.dir()
    found.sort()
    found2 = pygr.Data.dir('')
    found2.sort()
    assert found == found2


def check_dir_download(self):
    found = pygr.Data.dir(download=True)
    found.sort()
    found2 = pygr.Data.dir('', download=True)
    found2.sort()
    assert len(found) == 0
    assert found == found2


def check_dir_re(self):
    expected=['Bio.Annotation.annoDB', 'Bio.Annotation.map',
                'Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap']
    expected.sort()
    found = pygr.Data.dir('^Bio', 'r')
    found.sort()
    assert found == expected

    expected = ['Bio.Seq.Swissprot.sp42', 'Bio.Seq.spmap']
    expected.sort()
    found = pygr.Data.dir('^Bio\..+\.sp', 'r')
    found.sort()
    assert found == expected


def check_bind(self):
    sp = pygr.Data.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    trypsin = sp['PRCA_ANAVA']
    assert hbb.buddy == trypsin, 'automatic schema attribute binding'


def check_bind2(self):
    sp = pygr.Data.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    exons = hbb.exons.keys()
    assert len(exons) == 1, 'number of expected annotations'
    annoDB = pygr.Data.Bio.Annotation.annoDB()
    exon = annoDB[1]
    assert exons[0] == exon, 'test annotation comparison'
    assert exons[0].pathForward is exon, 'annotation parent match'
    assert exons[0].sequence == hbb[10:50], 'annotation to sequence match'
    onc = sp['HBB1_ONCMY']
    try:
        exons = onc.exons.keys()
        raise ValueError('failed to catch query with no annotations')
    except KeyError:
        pass


class Sequence_Test(TestBase):

    def setUp(self, *args, **kwargs):
        TestBase.setUp(self, *args, **kwargs)
        populate_swissprot()
        pygr.Data.save() # finally save everything
        pygr.Data.clear_cache() # force all requests to reload

    def test_match(self):
        "Test matching sequences"
        check_match(self)

    def test_dir(self):
        "Test labels"
        check_dir(self)
        check_dir_noargs(self)
        check_dir_re(self)

    def test_bind(self):
        "Test bind"
        check_bind(self)
        check_bind2(self)

    def test_schema(self):
        "Test schema"
        sp_hbb1 = testutil.datafile('sp_hbb1')
        sp2 = seqdb.BlastDB(sp_hbb1)
        sp2.__doc__ = 'another sp'
        pygr.Data.Bio.Seq.sp2 = sp2
        sp = pygr.Data.Bio.Seq.Swissprot.sp42()
        m = mapping.Mapping(sourceDB=sp, targetDB=sp2)
        m.__doc__ = 'sp -> sp2'
        pygr.Data.Bio.Seq.testmap = m
        pygr.Data.schema.Bio.Seq.testmap = pygr.Data.OneToManyRelation(sp, sp2)
        pygr.Data.save()

        pygr.Data.clear_cache()

        sp3 = seqdb.BlastDB(sp_hbb1)
        sp3.__doc__ = 'sp number 3'
        pygr.Data.Bio.Seq.sp3 = sp3
        sp2 = pygr.Data.Bio.Seq.sp2()
        m = mapping.Mapping(sourceDB=sp3, targetDB=sp2)
        m.__doc__ = 'sp3 -> sp2'
        pygr.Data.Bio.Seq.testmap2 = m
        pygr.Data.schema.Bio.Seq.testmap2 = pygr.Data.OneToManyRelation(sp3,
                                                                        sp2)
        # List all cached resources.
        l = pygr.Data.getResource.resourceCache.keys()
        l.sort()
        assert l == ['Bio.Seq.sp2', 'Bio.Seq.sp3', 'Bio.Seq.testmap2']
        pygr.Data.save()
        g = pygr.Data.getResource.writer.storage.graph
        expected = set(['Bio.Annotation.annoDB',
                     'Bio.Seq.Swissprot.sp42', 'Bio.Seq.sp2', 'Bio.Seq.sp3'])
        found = set(g.keys())
        self.EQ(len(expected - found), 0)


class SQL_Sequence_Test(Sequence_Test):

    def setUp(self):
        if not testutil.mysql_enabled():
            raise SkipTest("no MySQL installed")

        self.dbtable = testutil.temp_table_name() # create temp db tables
        Sequence_Test.setUp(self, pygrDataPath='mysql:' + self.dbtable,
                            mdbArgs=dict(createLayer='temp'))

    def tearDown(self):
        testutil.drop_tables(pygr.Data.getResource.writer.storage.cursor,
                             self.dbtable)


class InvalidPickle_Test(TestBase):

    def setUp(self):
        TestBase.setUp(self)

        class MyUnpicklableClass(object):
            pass

        MyUnpicklableClass.__module__ = '__main__'
        self.bad = MyUnpicklableClass()

        self.good = datetime.datetime.today()

    def test_invalid_pickle(self):
        "Testing an invalid pickle"
        s = pygr.Data.dumps(self.good) # should pickle with no errors
        try:
            s = pygr.Data.dumps(self.bad) # should raise exception
            msg = 'failed to catch bad attempt to invalid module ref'
            raise ValueError(msg)
        except pygr.Data.WorldbaseNoModuleError:
            pass


class XMLRPC_Test(TestBase):
    'create an XMLRPC server and access seqdb from it'

    def setUp(self):
        TestBase.setUp(self)
        populate_swissprot() # save some data
        pygr.Data.save() # finally save everything
        pygr.Data.clear_cache() # force all requests to reload

        res = ['Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap',
               'Bio.Annotation.annoDB', 'Bio.Annotation.map']
        self.server = testutil.TestXMLRPCServer(res, self.tempdir.path)

    def test_xmlrpc(self):
        "Test XMLRPC"
        pygr.Data.clear_cache() # force all requests to reload
        pygr.Data.update("http://localhost:%s" % self.server.port)

        check_match(self)
        check_dir(self)
        check_dir_noargs(self)
        check_dir_download(self)
        check_dir_re(self)
        check_bind(self)
        check_bind2(self)

        sb_hbb1 = testutil.datafile('sp_hbb1')
        sp2 = seqdb.BlastDB(sb_hbb1)
        sp2.__doc__ = 'another sp'
        try:
            pygr.Data.Bio.Seq.sp2 = sp2
            pygr.Data.save()
            msg = 'failed to catch bad attempt to write to XMLRPC server'
            raise KeyError(msg)
        except ValueError:
            pass

    def tearDown(self):
        'halt the test XMLRPC server'
        self.server.close()


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = restartIterator_megatest
import unittest
from testlib import testutil, PygrTestProgram
from pygr import worldbase


class RestartIterator_Test(unittest.TestCase):

    def setUp(self):
        self.msa = worldbase("Bio.MSA.UCSC.dm3_multiz15way")
        genome = worldbase("Bio.Seq.Genome.DROME.dm3")
        self.seq = -genome['chr3L'][10959977:10959996]

    def tearDown(self):
        # Restore original worldbase path to remedy lack of isolation
        # between tests from the same run
        worldbase.update(None)

    def test_restartIterator(self):
        try:
            self.msa[self.seq]
        except KeyError:
            # Shouldn't happen here but a valid response
            pass


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = runtest
#! /usr/bin/env python
"""
Test runner for main pygr tests.

Collects all files ending in _test.py and executes them.
"""

import os
import re
import shutil
import sys
import unittest

from testlib import testutil, testoptions
from testlib.unittest_extensions import PygrTestRunner
from pygr import logger

disable_threshold = 0                   # global logging override


def all_tests():
    "Returns all file names that end in _test.py"
    patt = re.compile("_test.py$")
    mods = os.listdir(os.path.normpath(os.path.dirname(__file__)))
    mods = filter(patt.search, mods)

    # some predictable order...
    mods.sort()
    return mods


def run(targets, options):
    "Imports and runs the modules names that are contained in the 'targets'"

    success = errors = skipped = 0

    # run the tests by importing the module and getting its test suite
    for name in targets:
        try:
            testutil.info('running tests for module %s' % name)
            l = unittest.TestLoader()
            suite = l.loadTestsFromName(name)

            runner = PygrTestRunner(verbosity=options.verbosity,
                                    descriptions=0)

            logger.disable(disable_threshold)  # set global override
            results = runner.run(suite)
            logger.disable(0)                  # clear global override

            # count tests and errors
            success += results.testsRun - \
                       len(results.errors) - \
                       len(results.failures) - \
                       len(results.skipped)

            errors += len(results.errors) + len(results.failures)
            skipped += len(results.skipped)

            # if we're in strict mode stop on errors
            if options.strict and errors:
                testutil.error("strict mode stops on errors")
                break

        except ImportError:
            testutil.error("unable to import module '%s'" % name)

    # summarize the run
    testutil.info('=' * 59)
    testutil.info('''\
%s tests passed, %s tests failed, %s tests skipped; %d total''' % \
                  (success, errors, skipped, success + errors + skipped))

    return (success, errors, skipped)

if __name__ == '__main__':
    # Make sure no messages are filtered out at first
    logger.disable(0)

    # gets the prebuild option parser
    parser = testoptions.option_parser()

    # parse the options
    options, args = parser.parse_args()

    # modules: from command line args or all modules
    targets = args or all_tests()

    # get rid of the .py ending in case full module names were passed in
    # the command line
    stripped_targets = []
    for t in targets:
        if t.endswith('.py'):
            t = t[:-3]
        stripped_targets.append(t)
    targets = stripped_targets

    if options.port:
        testutil.default_xmlrpc_port = options.port

    # exclusion mode
    if options.exclude:
        targets = [name for name in all_tests() if name not in targets]

    # disables debug messages at < 2 verbosity, debug+info at < 1
    if options.verbosity < 1:
        disable_threshold = 'INFO' # Should implicity disable DEBUG as well
    elif options.verbosity < 2:
        disable_threshold = 'DEBUG'

    # cleans full entire test directory
    if options.clean:
        testutil.TEMPROOT.reset()
        testutil.TEMPDIR = testutil.TEMPROOT.path # yikes!

        # list patterns matching files to be removed here
        patterns = [
            "*.seqlen", "*.pureseq", "*.nin", "*.pin", "*.psd",
            "*.psi", "*.psq", "*.psd", "*.nni", "*.nhr",
            "*.nsi", "*.nsd", "*.nsq", "*.nnd",
        ]
        testutil.remove_files(path=testutil.DATADIR, patterns=patterns)

    # run all the tests
    if options.coverage:
        good, bad, skip = testutil.generate_coverage(run, 'coverage',
                                                     targets=targets,
                                                     options=options)
    else:
        good, bad, skip = run(targets=targets, options=options)

    if bad:
        sys.exit(-1)

    sys.exit(0)

########NEW FILE########
__FILENAME__ = seqdb_test
"""
Tests for the pygr.seqdb module.
"""

import os
import unittest

from testlib import testutil, PygrTestProgram
from pygr.seqdb import SequenceDB, SequenceFileDB, PrefixUnionDict, \
     AnnotationDB, SeqPrefixUnionDict
from pygr.sequence import Sequence
from pygr.cnestedlist import NLMSA
import gc
from pygr.annotation import AnnotationDB, AnnotationSeq, AnnotationSlice, \
    AnnotationServer, AnnotationClient

# utility classes for the SequenceDB tests

_fake_seq = "ATCGAGAGCCAGAATGACGGGACCATTAG"


class _SimpleFakeSequence(Sequence):

    def __init__(self, db, id):
        assert id == "foo"
        Sequence.__init__(self, _fake_seq, "foo")

    def __len__(self):
        return len(self.seq)

    def strslice(self, start, end):
        return self.seq[start:end]


class _SimpleFakeInfoObj(object):

    def __init__(self, length):
        self.length = length


class _SimpleFakeSeqDB(SequenceDB):

    def __init__(self, *args, **kwargs):
        self.seqInfoDict = dict(foo=_SimpleFakeInfoObj(len(_fake_seq)))
        SequenceDB.__init__(self, *args, **kwargs)

###

class SequenceDB_Test(unittest.TestCase):

    def test_repr(self):
        "test the __repr__ function."

        db = _SimpleFakeSeqDB(itemClass=_SimpleFakeSequence)
        repr(db)

    def test_create_no_itemclass(self):
        # must supply an itemclass to SequenceDB!
        try:
            db = SequenceDB()
            assert 0, "should not reach this point"
        except TypeError:
            pass


class SequenceFileDB_Test(unittest.TestCase):
    """
    Test for all of the basic dictionary functions on 'SequenceFileDB',
    among other things.
    """

    def setUp(self):
        "Test setup"
        dnaseq = testutil.datafile('dnaseq.fasta')
        self.db = SequenceFileDB(dnaseq) # contains 'seq1', 'seq2'

        self.db._weakValueDict.clear()   # clear the cache

    def tearDown(self):
        self.db.close() # must close SequenceFileDB!

    def test_len(self):
        assert len(self.db) == 2

    def test_seqInfoDict_len(self):
        assert len(self.db.seqInfoDict) == 2

    def test_no_file_given(self):
        "Make sure that a TypeError is raised when no file is available"
        try:
            db = SequenceFileDB()
            assert 0, "should not reach this point"
        except TypeError:
            pass

    def test_seq_descriptor(self):
        "Check the '.seq' attribute (tied to a descriptor)"
        s = self.db['seq1']
        assert str(s) == str(s.seq)

    def test_cache(self):
        "SequenceDB cache test"
        assert len(self.db._weakValueDict) == 0
        seq1 = self.db['seq1']

        # cache populated?
        assert len(self.db._weakValueDict) == 1
        assert 'seq1' in self.db._weakValueDict

        # cache functions?
        seq1_try2 = self.db['seq1']
        assert seq1 is seq1_try2

    def test_clear_cache(self):
        "SequenceDB clear_cache test"
        assert len(self.db._weakValueDict) == 0
        seq1 = self.db['seq1']

        # cache populated?
        assert len(self.db._weakValueDict) == 1
        assert 'seq1' in self.db._weakValueDict

        # clear_cache functions?
        self.db.clear_cache()
        seq1_try3 = self.db['seq1']
        assert seq1 is not seq1_try3

    def test_keys(self):
        "SequenceFileDB keys"
        k = self.db.keys()
        k.sort()
        assert k == ['seq1', 'seq2']

    def test_contains(self):
        "SequenceFileDB contains"
        assert 'seq1' in self.db, self.db.keys()
        assert 'seq2' in self.db
        assert 'foo' not in self.db

    def test_invert_class(self):
        "SequenceFileDB __invert__"
        seq = self.db['seq1']
        inversedb = ~self.db
        assert inversedb[seq] == 'seq1'
        assert seq in inversedb
        assert 'foo' not in inversedb

    def test_keys_info(self):
        "SequenceFileDB keys info"
        k = self.db.seqInfoDict.keys()
        k.sort()
        assert k == ['seq1', 'seq2']

    def test_contains_info(self):
        "SequenceFileDB contains info"
        assert 'seq1' in self.db.seqInfoDict
        assert 'seq2' in self.db.seqInfoDict
        assert 'foo' not in self.db.seqInfoDict

    def test_has_key(self):
        "SequenceFileDB has key"
        assert 'seq1' in self.db
        assert 'seq2' in self.db
        assert 'foo' not in self.db

    def test_get(self):
        "SequenceFileDB get"
        assert self.db.get('foo') is None
        assert self.db.get('seq1') is not None
        assert str(self.db.get('seq1')).startswith('atggtgtca')
        assert self.db.get('seq2') is not None
        assert str(self.db.get('seq2')).startswith('GTGTTGAA')

    def test_items(self):
        "SequenceFileDB items"
        i = [k for (k, v) in self.db.items()]
        i.sort()
        assert i == ['seq1', 'seq2']

    def test_iterkeys(self):
        "SequenceFileDB iterkeys"
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik

    def test_itervalues(self):
        "SequenceFileDB itervalues"
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv == iv

    def test_iteritems(self):
        "SequenceFileDB iteritems"
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii

    def test_readonly(self):
        "SequenceFileDB readonly"
        try:
            self.db.copy()          # what should 'copy' do on SequenceFileDB?
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.clear()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.setdefault('foo')
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.pop()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.popitem()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.update({})
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass

    # test some things other than dict behavior
    def test_keyerror(self):
        """SequenceFileDB keyerror.
        Make sure that the SequenceFileDB KeyError is informative."""
        try:
            self.db['foo']
        except KeyError, e:
            assert "no key 'foo' in database <SequenceFileDB" in str(e), str(e)

    def test_close(self):
        """SequenceFileDB close.
        Check closing behavior; access after close() --> ValueError """
        self.db.close()
        self.db.close() # closing twice should not raise an error
        try:
            len(self.db)
            assert 0, 'Failed to catch invalid shelve access!'
        except ValueError:
            pass
        try:
            self.db['seq1']
            assert 0, 'Failed to catch invalid shelve access!'
        except ValueError:
            pass


class SequenceFileDB_Creation_Test(unittest.TestCase):
    """
    Test some of the nastier / more polluting creation code in an
    isolated (and slower...) class that cleans up after itself.
    """

    def trash_intermediate_files(self):
        seqlen = testutil.datafile('dnaseq.fasta.seqlen')
        pureseq = testutil.datafile('dnaseq.fasta.pureseq')
        try:
            os.unlink(seqlen)
            os.unlink(pureseq)
        except OSError:
            pass

    def setUp(self):
        "Test setup"
        self.trash_intermediate_files()
        self.dbfile = testutil.datafile('dnaseq.fasta')

    def tearDown(self):
        self.trash_intermediate_files()

    def test_basic_construction(self):
        db = SequenceFileDB(self.dbfile)
        try:
            assert str(db.get('seq1')).startswith('atggtgtca')
            assert str(db.get('seq2')).startswith('GTGTTGAA')
        finally:
            db.close()

    def test_build_seqLenDict_with_reader(self):
        "Test that building things works properly when specifying a reader."

        class InfoBag(object):

            def __init__(self, **kw):
                self.__dict__.update(kw)

        # first, load the db & save the sequence info in a list
        l = []
        db = SequenceFileDB(self.dbfile)
        try:
            for k, v in db.items():
                info = InfoBag(id=k, length=len(v), sequence=str(v))
                l.append(info)
        finally:
            # now, erase the existing files, and recreate the db.
            db.close()
        self.trash_intermediate_files()

        # create a fake reader with access to the saved info
        def my_fake_reader(fp, filename, info_list=l):
            return info_list

        # now try creating with the fake reader
        db = SequenceFileDB(self.dbfile, reader=my_fake_reader)

        # did it work?
        try:
            assert str(db.get('seq1')).startswith('atggtgtca')
            assert str(db.get('seq2')).startswith('GTGTTGAA')
        finally:
            db.close()

    def test_build_seqLenDict_with_bad_reader(self):
        "Test that building things fails properly with a bad reader."

        class InfoBag(object):

            def __init__(self, **kw):
                self.__dict__.update(kw)

        # first, load the db & save the sequence info in a list
        l = []
        db = SequenceFileDB(self.dbfile)
        try:
            for k, v in db.items():
                info = InfoBag(id=k, length=0, sequence=str(v))
                l.append(info)
        finally:
            # now, erase the existing files, and recreate the db.
            db.close()
        self.trash_intermediate_files()

        # create a fake reader with access to the saved info
        def my_fake_reader(fp, filename, info_list=l):
            return info_list

        # now try creating with the fake reader
        try:
            db = SequenceFileDB(self.dbfile, reader=my_fake_reader)
            try:
                assert 0, "should not reach here; db construction should fail!"
            finally:
                db.close()
        except ValueError:
            pass                        # ValueError is expected


def close_pud_dicts(pud):
    """Close all seq dbs indexed in a PrefixUnionDict """
    for db in pud.dicts:
        db.close()


class PrefixUnionDict_Creation_Test(unittest.TestCase):
    """
    Test PUD creation options.
    """

    def setUp(self):
        self.dbfile = testutil.datafile('dnaseq.fasta')

    def test_empty_create(self):
        db = PrefixUnionDict()
        assert len(db) == 0

    def test_headerfile_create(self):
        header = testutil.datafile('prefixUnionDict-1.txt')
        db = PrefixUnionDict(filename=header)
        try:
            assert len(db) == 2
            assert 'a.seq1' in db
        finally:
            close_pud_dicts(db)

    def test_headerfile_create_conflict(self):
        "test non-empty prefixDict with a passed in PUD header file: conflict"
        subdb = SequenceFileDB(self.dbfile)
        try:
            header = testutil.datafile('prefixUnionDict-1.txt')
            try:
                db = PrefixUnionDict(filename=header,
                                     prefixDict={'foo': subdb})
                assert 0, "should not get here"
            except TypeError:
                pass
        finally:
            subdb.close()

    def test_multiline_headerfile_create(self):
        header = testutil.datafile('prefixUnionDict-2.txt')
        db = PrefixUnionDict(filename=header)
        try:
            assert len(db) == 4
            assert 'a.seq1' in db
            assert 'b.seq1' in db
        finally:
            close_pud_dicts(db)

    def test_headerfile_create_with_trypath(self):
        header = testutil.datafile('prefixUnionDict-1.txt')
        db = PrefixUnionDict(filename=header,
                             trypath=[os.path.dirname(header)])
        try:
            assert len(db) == 2, db.prefixDict
        finally:
            close_pud_dicts(db)

    def test_headerfile_create_fail(self):
        header = testutil.datafile('prefixUnionDict-3.txt')
        try:
            db = PrefixUnionDict(filename=header)
            assert 0, "should not reach this point"
        except IOError:
            pass
        except AssertionError:
            close_pud_dicts(db)
            raise

    def test_headerfile_write(self):
        header = testutil.datafile('prefixUnionDict-2.txt')
        db = PrefixUnionDict(filename=header)
        try:
            assert len(db) == 4
            assert 'a.seq1' in db
            assert 'b.seq1' in db

            output = testutil.tempdatafile('prefixUnionDict-write.txt')
            db.writeHeaderFile(output)
        finally:
            close_pud_dicts(db)

        db2 = PrefixUnionDict(filename=output,
                               trypath=[os.path.dirname(header)])
        try:
            assert len(db2) == 4
            assert 'a.seq1' in db2
            assert 'b.seq1' in db2
        finally:
            close_pud_dicts(db2)

    def test_headerfile_write_fail(self):
        subdb = SequenceFileDB(self.dbfile)
        try:
            del subdb.filepath  # remove 'filepath' attribute for test
            db = PrefixUnionDict({'prefix': subdb})

            assert len(db) == 2
            assert 'prefix.seq1' in db

            output = testutil.tempdatafile('prefixUnionDict-write-fail.txt')
            try:
                db.writeHeaderFile(output)
            except AttributeError:
                pass
        finally:
            subdb.close() # closes both db and subdb


class PrefixUnionDict_Test(unittest.TestCase):
    """
    Test for all of the basic dictionary functions on 'PrefixUnionDict'.
    """

    def setUp(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)     # contains 'seq1', 'seq2'
        self.db = PrefixUnionDict({'prefix': seqdb})

    def tearDown(self):
        close_pud_dicts(self.db)

    def test_keys(self):
        "PrefixUnionDict keys"
        k = self.db.keys()
        k.sort()
        assert k == ['prefix.seq1', 'prefix.seq2']

    def test_contains(self):
        "PrefixUnionDict contains"
        # first, check "is this sequence name in the PUD?"-style contains.
        assert 'prefix.seq1' in self.db
        assert 'prefix.seq2' in self.db
        assert 'foo' not in self.db
        assert 'prefix.foo' not in self.db

        # now, check "is this sequence in the PUD?"
        seq = self.db['prefix.seq1']
        assert seq in self.db

        # finally, check failure: "is something other than str/seq in db"
        try:
            12345 in self.db
            assert 0, "should not get to this point"
        except AttributeError:
            pass

    def test_invert_class(self):
        "PrefixUnionDict __invert__"
        seq = self.db['prefix.seq1']
        inversedb = ~self.db
        assert inversedb[seq] == 'prefix.seq1'
        assert seq in inversedb
        assert 'foo' not in inversedb

    def test_funny_key(self):
        "check handling of ID containing multiple separators"
        dnaseq = testutil.datafile('funnyseq.fasta')
        seqdb = SequenceFileDB(dnaseq)     # contains 'seq1', 'seq2'
        try:
            pudb = PrefixUnionDict({'prefix': seqdb})
            seq = pudb['prefix.seq.1.more']
        finally:
            seqdb.close()

    def test_funny_key2(self):
        "check handling of ID containing multiple separators"
        dnaseq = testutil.datafile('funnyseq.fasta')
        seqdb = SequenceFileDB(dnaseq)     # contains 'seq1', 'seq2'
        try:
            pudb = PrefixUnionDict({'prefix': seqdb})
            seq = pudb['prefix.seq.2.even.longer']
        finally:
            seqdb.close()

    def test_has_key(self):
        "PrefixUnionDict has key"
        assert 'prefix.seq1' in self.db
        assert 'prefix.seq2' in self.db
        assert 'prefix.foo' not in self.db
        assert 'foo' not in self.db

    def test_get(self):
        "PrefixUnionDict get"
        assert self.db.get('foo') is None
        assert self.db.get('prefix.foo') is None
        assert self.db.get('prefix.seq1') is not None
        assert str(self.db.get('prefix.seq1')).startswith('atggtgtca')
        assert self.db.get('prefix.seq2') is not None
        assert str(self.db.get('prefix.seq2')).startswith('GTGTTGAA')
        assert self.db.get('foo.bar') is None
        assert self.db.get(12345) is None

    def test_get_prefix_id(self):
        try:
            self.db.get_prefix_id(12345)
            assert 0, "should not get here"
        except KeyError:
            pass

    def test_getName(self):
        seq1 = self.db['prefix.seq1']
        name = self.db.getName(seq1)
        assert name == 'prefix.seq1'

    def test_items(self):
        "PrefixUnionDict items"
        i = [k for (k, v) in self.db.items()]
        i.sort()
        assert i == ['prefix.seq1', 'prefix.seq2']

    def test_iterkeys(self):
        "PrefixUnionDict iterkeys"
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik

    def test_itervalues(self):
        "PrefixUnionDict itervalues"
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv == iv

    def test_iteritems(self):
        "PrefixUnionDict iteritems"
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii

    # test some things other than dict behavior
    def test_keyerror(self):
        "PrefixUnionDict keyerror"
        "Make sure that the PrefixUnionDict KeyError is informative."
        try:
            self.db['prefix.foo']
        except KeyError, e:
            assert "no key 'foo' in " in str(e), str(e)
        try:
            self.db['foo']
        except KeyError, e:
            assert "invalid id format; no prefix: foo" in str(e), str(e)

    def test_readonly(self):
        "PrefixUnionDict readonly"
        try:
            self.db.copy()              # what should 'copy' do on PUD?
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:                           # what should 'setdefault' do on PUD?
            self.db.setdefault('foo')
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:                           # what should 'update' do on PUD?
            self.db.update({})
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.clear()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.pop()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.popitem()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass

    def test_seqInfoDict(self):
        seqInfoDict = self.db.seqInfoDict

        keylist = seqInfoDict.keys()
        keylist.sort()

        keylist2 = list(seqInfoDict)
        keylist2.sort()

        assert keylist == ['prefix.seq1', 'prefix.seq2']
        assert keylist2 == ['prefix.seq1', 'prefix.seq2']

        itemlist = list(seqInfoDict.iteritems())
        itemlist.sort()
        ((n1, i1), (n2, i2)) = itemlist

        ii1, ii2 = list(seqInfoDict.itervalues())

        s1i = seqInfoDict['prefix.seq1']
        s2i = seqInfoDict['prefix.seq2']

        assert n1 == 'prefix.seq1'
        assert (i1.id, i1.db) == (s1i.id, s1i.db)
        assert (ii1.id, ii1.db) == (s1i.id, s1i.db)
        assert n2 == 'prefix.seq2'
        assert (i2.id, i2.db) == (s2i.id, s2i.db)
        assert (ii2.id, ii2.db) == (s2i.id, s2i.db)

        assert 'prefix.seq1' in seqInfoDict


class PrefixUnionMemberDict_Test(unittest.TestCase):

    def setUp(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)     # contains 'seq1', 'seq2'
        self.db = PrefixUnionDict({'prefix': seqdb})
        self.mdb = self.db.newMemberDict()

    def tearDown(self):
        close_pud_dicts(self.db)

    def test_basic(self):
        self.mdb['prefix'] = 'this is from seqdb dnaseq.fasta'
        seq = self.db['prefix.seq1']
        assert self.mdb[seq] == 'this is from seqdb dnaseq.fasta'

    def test_possible_keys(self):
        assert list(self.mdb.possibleKeys()) == ['prefix']

    def test_bad_prefix(self):
        try:
            self.mdb['foo'] = "xyz"
            assert 0, "should fail before this"
        except KeyError:
            pass

    def test_bad_keytype(self):
        try:
            self.mdb['some non-seq-obj']
            assert 0, "should fail before this"
        except TypeError:
            pass

    def test_default_val(self):
        self.mdb = self.db.newMemberDict(default='baz')
        seq = self.db['prefix.seq1']
        assert self.mdb[seq] == 'baz'

    def test_no_default_val(self):
        self.mdb = self.db.newMemberDict()
        seq = self.db['prefix.seq1']
        try:
            self.mdb[seq]
            assert 0, "should fail before this"
        except KeyError:
            pass


class SeqPrefixUnionDict_Test(unittest.TestCase):
    """
    Test SeqPrefixUnionDict.
    """

    def setUp(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        self.seqdb = SequenceFileDB(dnaseq)     # contains 'seq1', 'seq2'
        self.db = SeqPrefixUnionDict({'prefix': self.seqdb})

    def tearDown(self):
        self.seqdb.close()

    def test_basic_iadd(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)
        try:
            new_seq = seqdb['seq1']

            self.db += new_seq

            assert new_seq in self.db
            name = (~self.db)[new_seq]
            assert name == 'dnaseq.seq1', name

            ###

            seqdb2 = SequenceFileDB(dnaseq)
            try:
                # Munge the filepath for testing.
                seqdb2.filepath = 'foo'
                new_seq2 = seqdb2['seq1']

                self.db += new_seq2
                name2 = (~self.db)[new_seq2]
                assert name2 == 'foo.seq1', name2
            finally:
                seqdb2.close()
        finally:
            seqdb.close()
        # NOTE, the important thing here is less the specific names that
        # are given (which are based on filepath) but that different names
        # are created for the various sequences when they are added.

    def test_iadd_db_twice(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)
        try:
            new_seq = seqdb['seq1']

            self.db += new_seq
            name1 = (~self.db)[new_seq]

            self.db += new_seq              # should do nothing...
            name2 = (~self.db)[new_seq]
            assert name1 == name2           # ...leaving seq with same name.
        finally:
            seqdb.close()

    def test_iadd_user_seq(self):
        seq = Sequence('ATGGCAGG', 'foo')
        self.db += seq

        name = (~self.db)[seq]
        assert name == 'user.foo'       # created a new 'user' db.

        # ok, make sure it doesn't wipe out the old 'user' db...
        seq2 = Sequence('ATGGCAGG', 'foo2')
        self.db += seq2

        name = (~self.db)[seq2]
        assert name == 'user.foo2'

        first_name = (~self.db)[seq]
        assert first_name == 'user.foo'

    def test_iadd_duplicate_seqdb(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)
        try:
            seqdb2 = SequenceFileDB(dnaseq)
            try:
                new_seq = seqdb['seq1']
                new_seq2 = seqdb2['seq1']

                self.db += new_seq
                try:
                    self.db += new_seq2
                    assert 0, "should never reach this point"
                except ValueError:
                    pass
            finally:
                seqdb2.close()
        finally:
            seqdb.close()

    def test_no_db_info(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)
        try:
            new_seq = seqdb['seq1']

            assert getattr(seqdb, '_persistent_id', None) is None
            del seqdb.filepath

            self.db += new_seq
            name = (~self.db)[new_seq]
            assert name == 'noname0.seq1'
        finally:
            seqdb.close()

    def test_inverse_add_behavior(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)
        try:
            seq = seqdb['seq1']

            name = (~self.db)[seq]
        finally:
            seqdb.close() # only need to close if exception occurs

    def test_inverse_noadd_behavior(self):
        # compare with test_inverse_add_behavior...
        db = SeqPrefixUnionDict(addAll=False)
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)
        try:
            seq = seqdb['seq1']

            try:
                name = (~db)[seq]
                assert 0, "should not get here"
            except KeyError:
                pass
        finally:
            seqdb.close()


class SeqDBCache_Test(unittest.TestCase):

    def test_cache(self):
        "Sequence slice cache mechanics."

        dnaseq = testutil.datafile('dnaseq.fasta')
        db = SequenceFileDB(dnaseq)

        try:
            # create cache components
            cacheDict = {}
            cacheHint = db.cacheHint

            # get seq1
            seq1 = db['seq1']

            # _cache is only created on first cache attempt
            assert not hasattr(db, '_cache')

            # build an 'owner' object
            class AnonymousOwner(object):
                pass
            owner = AnonymousOwner()

            # save seq1 in cache
            cacheDict['seq1'] = (seq1.start, seq1.stop)
            cacheHint(cacheDict, owner)
            del cacheDict                   # 'owner' now holds reference

            # peek into _cache and assert that only the ival coordinates
            # are stored
            v = db._cache.values()[0]
            assert len(v['seq1']) == 2
            del v

            # force a cache access & check that now we've stored actual string
            ival = str(seq1[5:10])
            v = db._cache.values()[0]
            # ...check that we've stored actual string
            assert len(v['seq1']) == 3

            # again force cache access, this time to the stored sequence string
            ival = str(seq1[5:10])

            # now, eliminate all references to the cache proxy dict
            del owner

            # trash unused objects - not strictly necessary, because there are
            # no islands of circular references & so all objects are already
            # deallocated, but that's implementation dependent.
            gc.collect()

            # ok, cached values should now be gone.
            v = db._cache.values()
            assert len(v) == 0
        finally:
            db.close()

    def test_nlmsaslice_cache(self):
        "NLMSASlice sequence caching & removal"

        # set up sequences
        dnaseq = testutil.datafile('dnaseq.fasta')

        db = SequenceFileDB(dnaseq, autoGC=-1) # use pure WeakValueDict...
        try:
            gc.collect()
            assert len(db._weakValueDict)==0, '_weakValueDict should be empty'
            seq1, seq2 = db['seq1'], db['seq2']
            assert len(db._weakValueDict)==2, \
                    '_weakValueDict should have 2 seqs'

            # build referencing NLMSA
            mymap = NLMSA('test', 'memory', db, pairwiseMode=True)
            mymap += seq1
            mymap[seq1] += seq2
            mymap.build()

            # check: no cache
            assert not hasattr(db, '_cache'), 'should be no cache yet'

            seq1, seq2 = db['seq1'], db['seq2'] # re-retrieve
            # now retrieve a NLMSASlice, forcing entry of seq into cache
            ival = seq1[5:10]
            x = mymap[ival]

            assert len(db._cache.values()) != 0

            n1 = len(db._cache)
            assert n1 == 1, "should be exactly one cache entry, not %d" % \
                    (n1, )

            # ok, now trash referencing arguments & make sure of cleanup
            del x
            gc.collect()

            assert len(db._cache.values()) == 0


            n2 = len(db._cache)
            assert n2 == 0, '%d objects remain; cache memory leak!' % n2
            # FAIL because of __dealloc__ error in cnestedlist.NLMSASlice.

            # Drop our references, the cache should empty.
            del mymap, ival, seq1, seq2
            gc.collect()
            # check that db._weakValueDict cache is empty
            assert len(db._weakValueDict)==0, '_weakValueDict should be empty'
        finally:
            db.close()

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = sequence_test
import unittest
from testlib import testutil, PygrTestProgram
from pygr import sequence


class Sequence_Test(unittest.TestCase):
    'basic sequence class tests'

    def setUp(self):
        self.seq = sequence.Sequence('atttgactatgctccag', 'foo')

    def test_length(self):
        "Sequence lenght"
        assert len(self.seq) == 17

    def test_slice(self):
        "Sequence slice"
        assert str(self.seq[5:10]) == 'actat'

    def test_slicerc(self):
        "Sequence slice then reverse complement"
        assert str(-(self.seq[5:10])) == 'atagt'

    def test_rcslice(self):
        "Sequence reverse complement then slice"
        assert str((-self.seq)[5:10]) == 'gcata'

    def test_truncate(self):
        "Sequence truncate"
        assert str(self.seq[-202020202:5]) == 'atttg'
        assert self.seq[-202020202:5] == self.seq[0:5]
        assert self.seq[-2020202:] == self.seq
        assert str(self.seq[-202020202:-5]) == 'atttgactatgc'
        assert str(self.seq[-5:2029]) == 'tccag'
        assert str(self.seq[-5:]) == 'tccag'
        try:
            self.seq[999:10000]
            raise ValueError('failed to trap out of bounds slice')
        except IndexError:
            pass
        try:
            self.seq[-10000:-3000]
            raise ValueError('failed to trap out of bounds slice')
        except IndexError:
            pass
        try:
            self.seq[1000:]
            raise ValueError('failed to trap out of bounds slice')
        except IndexError:
            pass

    def test_rctruncate(self):
        "Sequence reverse complement truncate"
        seq= -self.seq
        assert str(seq[-202020202:5]) == 'ctgga'
        assert seq[-202020202:5] == seq[0:5]
        assert seq[-2020202:] == seq
        assert str(seq[-202020202:-5]) == 'ctggagcatagt'
        assert str(seq[-5:2029]) == 'caaat'
        assert str(seq[-5:]) == 'caaat'
        try:
            seq[999:10000]
            raise ValueError('failed to trap out of bounds slice')
        except IndexError:
            pass
        try:
            seq[-10000:-3000]
            raise ValueError('failed to trap out of bounds slice')
        except IndexError:
            pass
        try:
            seq[1000:]
            raise ValueError('failed to trap out of bounds slice')
        except IndexError:
            pass

    def test_join(self):
        "Sequence join"
        assert str(self.seq[5:15] * self.seq[8:]) == 'atgctcc'

    def test_rcjoin(self):
        "Sequence reverse complement join"
        assert str((-(self.seq[5:10])) * ((-self.seq)[5:10])) == 'ata'

    def test_seqtype(self):
        "Sequence lenght"
        assert self.seq.seqtype() == sequence.DNA_SEQTYPE
        assert sequence.Sequence('auuugacuaugcuccag', 'foo').seqtype() == \
                         sequence.RNA_SEQTYPE
        assert sequence.Sequence('kqwestvvarphal', 'foo').seqtype() == \
                         sequence.PROTEIN_SEQTYPE

# @CTB
'''
#from pygrdata_test import PygrSwissprotBase
class Blast_Test(PygrSwissprotBase):
    'test basic blast functionality'
    @skip_errors(OSError, KeyError)
    def setup(self):
        PygrSwissprotBase.setup(self)
        import pygr.Data
        self.sp = pygr.Data.Bio.Seq.Swissprot.sp42()
        import os
        blastIndexPath = os.path.join(os.path.dirname(self.sp.filepath),
                                      'wikiwacky')
        self.sp.formatdb(blastIndexPath)
    def blast(self):
        hbb = self.sp['HBB1_TORMA']
        hits = self.sp.blast(hbb)
        edges = hits[hbb].edges(maxgap=1, maxinsert=1,
                                minAlignSize=14,pIdentityMin=0.5)
        for t in edges:
            assert len(t[0])>=14, 'result shorter than minAlignSize!'
        result = [(t[0], t[1], t[2].pIdentity()) for t in edges]
        store = PygrDataTextFile(os.path.join('results', 'seqdb1.pickle'))
        correct = store['hbb blast 1']
        assert approximate_cmp(result, correct, .0001) == 0, 'blast results should match'
        result = [(t[0], t[1], t[2].pIdentity()) for t in hits[hbb].generateSeqEnds()]
        correct = store['hbb blast 2']
        assert approximate_cmp(result, correct, .0001) == 0, 'blast results should match'
        trypsin = self.sp['PRCA_ANASP']
        try:
            hits[trypsin]
            raise ValueError('failed to catch bad alignment query')
        except KeyError:
            pass
class Blast_reindex_untest(Blast_Test):
    'test building blast indexes under a different name'
    @skip_errors(OSError, KeyError)
    def setup(self):
        PygrSwissprotBase.setup(self)
        import pygr.Data
        self.sp = pygr.Data.Bio.Seq.Swissprot.sp42()
        import os
        blastIndexPath = os.path.join(os.path.dirname(self.sp.filepath), 'wikiwacky')
        self.sp.formatdb()
        #self.sp.formatdb(blastIndexPath) # FORCE IT TO STORE INDEX WITH DIFFERENT NAME
        #print 'blastIndexPath is', self.sp.blastIndexPath

'''

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = sqlsequence_test
# test will be skipped if MySqlDB is unavailable

import string
import unittest
from testlib import testutil, SkipTest, PygrTestProgram
from pygr import sqlgraph, seqdb, classutil, logger


class DNASeqRow(seqdb.DNASQLSequence):
    def __len__(self): # just speed optimization
        return self._select('length(sequence)') # SQL SELECT expression


class SQLSequence_Test(unittest.TestCase):
    '''Basic SQL sequence class tests

    This test setup uses the common (?) method of having the
    SQLSequence objects created by a SQLTable object rather than
    instantiating the SQLSequence objects directly.
    '''
    _dbClass = sqlgraph.SQLTableNoCache
    _rowClass = DNASeqRow

    def setUp(self, serverInfo=None, dbname='test.sqlsequence_test'):
        if not testutil.mysql_enabled():
            raise SkipTest("no MySQL installed")

        createTable = 'CREATE TABLE %s (primary_id INTEGER PRIMARY KEY \
                %%(AUTO_INCREMENT)s, sequence TEXT)' % dbname

        self.db = self._dbClass(dbname, serverInfo=serverInfo,
                                itemClass=self._rowClass, dropIfExists=True,
                                createTable=createTable,
                                attrAlias=dict(seq='sequence'))

        self.db.cursor.execute("""\
INSERT INTO %s (sequence) VALUES ('\
CACCCTGCCCCATCTCCCCAGCCTGGCCCCTCGTGTCTCAGAACCCTCGGGGGGAGGCACAGAAGCCTTCGGGG')"""
                               % dbname)

        self.db.cursor.execute("""\
        INSERT INTO %s (sequence)
              VALUES ('GAAAGAAAGAAAGAAAGAAAGAAAGAGAGAGAGAGAGACAGAAG')
        """ % dbname)

        self.row1 = self.db[1]
        self.row2 = self.db[2]
        self.EQ = self.assertEqual

    def tearDown(self):
        self.db.cursor.execute('drop table if exists test.sqlsequence_test')

    def test_print(self):
        "Testing identities"
        self.EQ(str(self.row2), 'GAAAGAAAGAAAGAAAGAAAGAAAGAGAGAGAGAGAGACAGAAG')
        self.EQ(repr(self.row2), '2[0:44]')

    def test_len(self):
        "Testing lengths"
        self.EQ(len(self.row2), 44)

    def test_strslice(self):
        "Testing slices"
        self.EQ(self.row2.strslice(3, 10), 'AGAAAGA')

    def init_subclass_test(self):
        "Testing subclassing"
        self.row2._init_subclass(self.db)

class SQLSeqCached_Test(SQLSequence_Test):
    _dbClass = sqlgraph.SQLTable
    _rowClass = sqlgraph.DNASQLSequenceCached


class SQLiteSequence_Test(testutil.SQLite_Mixin, SQLSequence_Test):
    def sqlite_load(self):
        SQLSequence_Test.setUp(self, self.serverInfo, 'sqlsequence_test')

class SQLiteSeqCached_Test(SQLiteSequence_Test):
    _dbClass = sqlgraph.SQLTable
    _rowClass = sqlgraph.DNASQLSequenceCached


def get_suite():
    "Returns the testsuite"
    tests = []

    # detect mysql
    if testutil.mysql_enabled():
        tests.append(SQLSequence_Test)
    else:
        testutil.info('*** skipping SQLSequence_Test')
    if testutil.sqlite_enabled():
        tests.append(SQLiteSequence_Test)
    else:
        testutil.info('*** skipping SQLSequence_Test')

    return testutil.make_suite(tests)

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = sqltable_test
import os
import random
import string
import unittest

from testlib import testutil, PygrTestProgram, SkipTest
from pygr.sqlgraph import SQLTable, SQLTableNoCache, SQLTableClustered,\
     MapView, GraphView, DBServerInfo, import_sqlite
from pygr import logger


def entrap(klass):
    'return a function to intercept any calls to generic_iterator() method'

    def catch_iterator(self, *args, **kwargs):
        try:
            assert not self.catchIter, 'this should not iterate!'
        except AttributeError:
            pass
        return klass.generic_iterator(self, *args, **kwargs)
    return catch_iterator


class SQLTableCatcher(SQLTable):
    generic_iterator = entrap(SQLTable)


class SQLTableNoCacheCatcher(SQLTableNoCache):
    generic_iterator = entrap(SQLTableNoCache)


class SQLTableClusteredCatcher(SQLTableClustered):
    generic_iterator = entrap(SQLTableClustered)


class SQLTable_Setup(unittest.TestCase):
    tableClass = SQLTableCatcher
    serverArgs = {}
    loadArgs = {}

    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        # share conn for all tests
        self.serverInfo = DBServerInfo(** self.serverArgs)

    def setUp(self):
        if not testutil.mysql_enabled():
            raise SkipTest("no MySQL installed")
        self.load_data(writeable=self.writeable, ** self.loadArgs)

    def load_data(self, tableName='test.sqltable_test', writeable=False,
                  dbargs={}, sourceDBargs={}, targetDBargs={}):
        'create 3 tables and load 9 rows for our tests'
        self.tableName = tableName
        self.joinTable1 = joinTable1 = tableName + '1'
        self.joinTable2 = joinTable2 = tableName + '2'
        createTable = 'CREATE TABLE %s (primary_id INTEGER PRIMARY KEY \
                %%(AUTO_INCREMENT)s, seq_id TEXT, start INTEGER, \
                stop INTEGER)' % tableName
        self.db = self.tableClass(tableName, dropIfExists=True,
                                  serverInfo=self.serverInfo,
                                  createTable=createTable,
                                  writeable=writeable,
                                  attrAlias=dict(sequence_id='seq_id',
                                                 minStop="min(stop)"),
                                  **dbargs)
        self.sourceDB = self.tableClass(joinTable1, serverInfo=self.serverInfo,
                                        dropIfExists=True, createTable="""\
        CREATE TABLE %s (my_id INTEGER PRIMARY KEY,
              other_id VARCHAR(16))
        """ % joinTable1, **sourceDBargs)
        self.targetDB = self.tableClass(joinTable2, serverInfo=self.serverInfo,
                                        dropIfExists=True, createTable="""\
        CREATE TABLE %s (third_id INTEGER PRIMARY KEY,
              other_id VARCHAR(16))
        """ % joinTable2, **targetDBargs)
        sql = """
            INSERT INTO %s (seq_id, start, stop) VALUES ('seq1', 0, 10)
            INSERT INTO %s (seq_id, start, stop) VALUES ('seq2', 5, 15)
            INSERT INTO %s VALUES (2,'seq2')
            INSERT INTO %s VALUES (3,'seq3')
            INSERT INTO %s VALUES (4,'seq4')
            INSERT INTO %s VALUES (7, 'seq2')
            INSERT INTO %s VALUES (99, 'seq3')
            INSERT INTO %s VALUES (6, 'seq4')
            INSERT INTO %s VALUES (8, 'seq4')
        """ % tuple(([tableName]*2) + ([joinTable1]*3) + ([joinTable2]*4))
        for line in sql.strip().splitlines(): # insert our test data
            self.db.cursor.execute(line.strip())

        # Another table, for the "ORDER BY" test
        self.orderTable = tableName + '_orderBy'
        self.db.cursor.execute('DROP TABLE IF EXISTS %s' % self.orderTable)
        self.db.cursor.execute('CREATE TABLE %s (id INTEGER PRIMARY KEY, \
                               number INTEGER, letter VARCHAR(1))'
                               % self.orderTable)
        for row in range(0, 10):
            self.db.cursor.execute('INSERT INTO %s VALUES (%d, %d, \'%s\')' %
                                   (self.orderTable, row,
                                    random.randint(0, 99),
                                    string.lowercase[random.randint(0,
                                                          len(string.lowercase)
                                                                    - 1)]))

    def tearDown(self):
        self.db.cursor.execute('drop table if exists %s' % self.tableName)
        self.db.cursor.execute('drop table if exists %s' % self.joinTable1)
        self.db.cursor.execute('drop table if exists %s' % self.joinTable2)
        self.db.cursor.execute('drop table if exists %s' % self.orderTable)
        self.serverInfo.close()


class SQLTable_Test(SQLTable_Setup):
    writeable = False # read-only database interface

    def test_keys(self):
        k = self.db.keys()
        k.sort()
        assert k == [1, 2]

    def test_len(self):
        self.db.catchIter = True
        assert len(self.db) == len(self.db.keys())

    def test_contains(self):
        self.db.catchIter = True
        assert 1 in self.db
        assert 2 in self.db
        assert 'foo' not in self.db

    def test_has_key(self):
        self.db.catchIter = True
        assert 1 in self.db
        assert 2 in self.db
        assert 'foo' not in self.db

    def test_get(self):
        self.db.catchIter = True
        assert self.db.get('foo') is None
        assert self.db.get(1) == self.db[1]
        assert self.db.get(2) == self.db[2]

    def test_items(self):
        i = [k for (k, v) in self.db.items()]
        i.sort()
        assert i == [1, 2]

    def test_iterkeys(self):
        kk = self.db.keys()
        ik = list(self.db.iterkeys())
        assert kk == ik

    def test_pickle(self):
        kk = self.db.keys()
        import pickle
        s = pickle.dumps(self.db)
        db = pickle.loads(s)
        try:
            ik = list(db.iterkeys())
            assert kk == ik
        finally:
            db.serverInfo.close() # close extra DB connection

    def test_itervalues(self):
        kv = self.db.values()
        iv = list(self.db.itervalues())
        assert kv == iv

    def test_itervalues_long(self):
        """test iterator isolation from queries run inside iterator loop """
        sql = 'insert into %s (start) values (1)' % self.tableName
        for i in range(40000): # insert 40000 rows
            self.db.cursor.execute(sql)
        iv = []
        for o in self.db.itervalues():
            status = 99 in self.db # make it do a query inside iterator loop
            iv.append(o.id)
        kv = [o.id for o in self.db.values()]
        assert len(kv) == len(iv)
        assert kv == iv

    def test_iteritems(self):
        ki = self.db.items()
        ii = list(self.db.iteritems())
        assert ki == ii

    def test_readonly(self):
        'test error handling of write attempts to read-only DB'
        self.db.catchIter = True # no iter expected in this test!
        try:
            self.db.new(seq_id='freddy', start=3000, stop=4500)
            raise AssertionError('failed to trap attempt to write to db')
        except ValueError:
            pass
        o = self.db[1]
        try:
            self.db[33] = o
            raise AssertionError('failed to trap attempt to write to db')
        except ValueError:
            pass
        try:
            del self.db[2]
            raise AssertionError('failed to trap attempt to write to db')
        except ValueError:
            pass

    def test_orderBy(self):
        'test iterator with orderBy, iterSQL, iterColumns'
        self.targetDB.catchIter = True # should not iterate
        # Force it to use multiple queries to finish.
        self.targetDB.arraysize = 2
        result = self.targetDB.keys()
        assert result == [6, 7, 8, 99]
        self.targetDB.catchIter = False # next statement will iterate
        assert result == list(iter(self.targetDB))
        self.targetDB.catchIter = True # should not iterate
        self.targetDB.orderBy = 'ORDER BY other_id'
        result = self.targetDB.keys()
        assert result == [7, 99, 6, 8]
        self.targetDB.catchIter = False # next statement will iterate
        if self.serverInfo._serverType == 'mysql' \
               and self.serverInfo.custom_iter_keys: # only test this for mysql
            try:
                assert result == list(iter(self.targetDB))
                raise AssertionError('failed to trap missing iterSQL attr')
            except AttributeError:
                pass
        self.targetDB.iterSQL = 'WHERE other_id>%s' # tell it how to slice
        self.targetDB.iterColumns = ['other_id']
        assert result == list(iter(self.targetDB))
        result = self.targetDB.values()
        assert result == [self.targetDB[7], self.targetDB[99],
                          self.targetDB[6], self.targetDB[8]]
        assert result == list(self.targetDB.itervalues())
        result = self.targetDB.items()
        assert result == [(7, self.targetDB[7]), (99, self.targetDB[99]),
                          (6, self.targetDB[6]), (8, self.targetDB[8])]
        assert result == list(self.targetDB.iteritems())
        import pickle
        s = pickle.dumps(self.targetDB) # test pickling & unpickling
        db = pickle.loads(s)
        try:
            correct = self.targetDB.keys()
            result = list(iter(db))
            assert result == correct
        finally:
            db.serverInfo.close() # close extra DB connection

    def test_orderby_random(self):
        'test orderBy in SQLTable'
        if self.serverInfo._serverType == 'mysql' \
               and self.serverInfo.custom_iter_keys:
            try:
                byNumber = self.tableClass(self.orderTable, arraysize=2,
                                           serverInfo=self.serverInfo,
                                           orderBy='ORDER BY number')
                raise AssertionError('failed to trap orderBy without iterSQL!')
            except ValueError:
                pass
        byNumber = self.tableClass(self.orderTable, serverInfo=self.serverInfo,
                                   arraysize=2, orderBy='ORDER BY number,id',
                          iterSQL='WHERE number>%s or (number=%s and id>%s)',
                                   iterColumns=('number', 'number', 'id'))
        bv = [val.number for val in byNumber.values()]
        sortedBV = bv[:]
        sortedBV.sort()
        assert sortedBV == bv
        bv = [val.number for val in byNumber.itervalues()]
        assert sortedBV == bv

        byLetter = self.tableClass(self.orderTable, serverInfo=self.serverInfo,
                                   arraysize=2, orderBy='ORDER BY letter,id',
                            iterSQL='WHERE letter>%s or (letter=%s and id>%s)',
                                   iterColumns=('letter', 'letter', 'id'))
        bl = [val.letter for val in byLetter.values()]
        sortedBL = bl[:]
        assert sortedBL == bl
        bl = [val.letter for val in byLetter.itervalues()]
        assert sortedBL == bl

    def test_attraliases(self):
        'test aliases defined with attrAlias'
        self.db[1].sequence_id
        self.db[1].minStop

    ### @CTB need to test write access

    def test_mapview(self):
        'test MapView of SQL join'
        self.sourceDB.catchIter = self.targetDB.catchIter = True
        m = MapView(self.sourceDB, self.targetDB, """\
        SELECT t2.third_id FROM %s t1, %s t2
           WHERE t1.my_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1, self.joinTable2), serverInfo=self.serverInfo)
        assert m[self.sourceDB[2]] == self.targetDB[7]
        assert m[self.sourceDB[3]] == self.targetDB[99]
        assert self.sourceDB[2] in m
        try:
            d = m[self.sourceDB[4]]
            raise AssertionError('failed to trap non-unique mapping')
        except KeyError:
            pass
        try:
            r = ~m
            raise AssertionError('failed to trap non-invertible mapping')
        except ValueError:
            pass
        self.sourceDB.cursor.execute("INSERT INTO %s VALUES (5,'seq78')"
                                     % self.sourceDB.name)
        assert len(self.sourceDB) == 4
        self.sourceDB.catchIter = False # next step will cause iteration
        assert len(m) == 2
        l = m.keys()
        l.sort()
        correct = [self.sourceDB[2], self.sourceDB[3]]
        correct.sort()
        assert l == correct

    def test_mapview_inverse(self):
        'test inverse MapView of SQL join'
        self.sourceDB.catchIter = self.targetDB.catchIter = True
        m = MapView(self.sourceDB, self.targetDB, """\
        SELECT t2.third_id FROM %s t1, %s t2
           WHERE t1.my_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1, self.joinTable2), serverInfo=self.serverInfo,
                    inverseSQL="""\
        SELECT t1.my_id FROM %s t1, %s t2
           WHERE t2.third_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1, self.joinTable2))
        r = ~m # get the inverse
        assert self.sourceDB[2] == r[self.targetDB[7]]
        assert self.sourceDB[3] == r[self.targetDB[99]]
        assert self.targetDB[7] in r

        m = ~r # get the inverse of the inverse!
        assert m[self.sourceDB[2]] == self.targetDB[7]
        assert m[self.sourceDB[3]] == self.targetDB[99]
        assert self.sourceDB[2] in m
        try:
            d = m[self.sourceDB[4]]
            raise AssertionError('failed to trap non-unique mapping')
        except KeyError:
            pass

    def test_graphview(self):
        'test GraphView of SQL join'
        self.sourceDB.catchIter = self.targetDB.catchIter = True
        m = GraphView(self.sourceDB, self.targetDB, """\
        SELECT t2.third_id FROM %s t1, %s t2
           WHERE t1.my_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1, self.joinTable2), serverInfo=self.serverInfo)
        d = m[self.sourceDB[4]]
        assert len(d) == 2
        assert self.targetDB[6] in d and self.targetDB[8] in d
        assert self.sourceDB[2] in m

        self.sourceDB.cursor.execute("INSERT INTO %s VALUES (5,'seq78')"
                                     % self.sourceDB.name)
        assert len(self.sourceDB) == 4
        self.sourceDB.catchIter = False # next step will cause iteration
        assert len(m) == 3
        l = m.keys()
        l.sort()
        correct = [self.sourceDB[2], self.sourceDB[3], self.sourceDB[4]]
        correct.sort()
        assert l == correct

    def test_graphview_inverse(self):
        'test inverse GraphView of SQL join'
        self.sourceDB.catchIter = self.targetDB.catchIter = True
        m = GraphView(self.sourceDB, self.targetDB, """\
        SELECT t2.third_id FROM %s t1, %s t2
           WHERE t1.my_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1, self.joinTable2), serverInfo=self.serverInfo,
                    inverseSQL="""\
        SELECT t1.my_id FROM %s t1, %s t2
           WHERE t2.third_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1, self.joinTable2))
        r = ~m # get the inverse
        assert self.sourceDB[2] in r[self.targetDB[7]]
        assert self.sourceDB[3] in r[self.targetDB[99]]
        assert self.targetDB[7] in r
        d = r[self.targetDB[6]]
        assert len(d) == 1
        assert self.sourceDB[4] in d

        m = ~r # get inverse of the inverse!
        d = m[self.sourceDB[4]]
        assert len(d) == 2
        assert self.targetDB[6] in d and self.targetDB[8] in d
        assert self.sourceDB[2] in m


class SQLTable_No_SSCursor_Test(SQLTable_Test):
    serverArgs = dict(serverSideCursors=False)


class SQLTable_OldIter_Test(SQLTable_Test):
    serverArgs = dict(serverSideCursors=False,
                      blockIterators=False)


class SQLiteBase(testutil.SQLite_Mixin):

    def sqlite_load(self):
        self.load_data('sqltable_test', writeable=self.writeable,
                       ** self.loadArgs)


class SQLiteTable_Test(SQLiteBase, SQLTable_Test):
    pass


## class SQLitePickle_Test(SQLiteTable_Test):
##
##     def setUp(self):
##         """Pickle / unpickle our serverInfo before trying to use it """
##         SQLiteTable_Test.setUp(self)
##         self.serverInfo.close()
##         import pickle
##         s = pickle.dumps(self.serverInfo)
##         del self.serverInfo
##         self.serverInfo = pickle.loads(s)
##         self.db = self.tableClass(self.tableName, serverInfo=self.serverInfo)
##         self.sourceDB = self.tableClass(self.joinTable1,
##                                         serverInfo=self.serverInfo)
##         self.targetDB = self.tableClass(self.joinTable2,
##                                         serverInfo=self.serverInfo)


class SQLTable_NoCache_Test(SQLTable_Test):
    tableClass = SQLTableNoCacheCatcher


class SQLTableClustered_Test(SQLTable_Test):
    tableClass = SQLTableClusteredCatcher
    loadArgs = dict(dbargs=dict(clusterKey='seq_id', arraysize=2),
                    sourceDBargs=dict(clusterKey='other_id', arraysize=2),
                    targetDBargs=dict(clusterKey='other_id', arraysize=2))

    def test_orderBy(self): # neither of these tests useful in this context
        pass

    def test_orderby_random(self):
        pass

class SQLiteClustered_Test(SQLiteBase, SQLTableClustered_Test):
    pass

class SQLiteTable_NoCache_Test(SQLiteTable_Test):
    tableClass = SQLTableNoCache


class SQLTableRW_Test(SQLTable_Setup):
    'test write operations'
    writeable = True

    def test_new(self):
        'test row creation with auto inc ID'
        self.db.catchIter = True # no iter expected in this test
        n = len(self.db)
        o = self.db.new(seq_id='freddy', start=3000, stop=4500)
        assert len(self.db) == n + 1
        t = self.tableClass(self.tableName,
                            serverInfo=self.serverInfo) # requery the db
        t.catchIter = True # no iter expected in this test
        result = t[o.id]
        assert result.seq_id == 'freddy' and result.start==3000 \
               and result.stop==4500

    def test_new2(self):
        'check row creation with specified ID'
        self.db.catchIter = True # no iter expected in this test
        n = len(self.db)
        o = self.db.new(id=99, seq_id='jeff', start=3000, stop=4500)
        assert len(self.db) == n + 1
        assert o.id == 99
        t = self.tableClass(self.tableName,
                            serverInfo=self.serverInfo) # requery the db
        t.catchIter = True # no iter expected in this test
        result = t[99]
        assert result.seq_id == 'jeff' and result.start==3000 \
               and result.stop==4500

    def test_attr(self):
        'test changing an attr value'
        self.db.catchIter = True # no iter expected in this test
        o = self.db[2]
        assert o.seq_id == 'seq2'
        o.seq_id = 'newval' # overwrite this attribute
        assert o.seq_id == 'newval' # check cached value
        t = self.tableClass(self.tableName,
                            serverInfo=self.serverInfo) # requery the db
        t.catchIter = True # no iter expected in this test
        result = t[2]
        assert result.seq_id == 'newval'

    def test_delitem(self):
        'test deletion of a row'
        self.db.catchIter = True # no iter expected in this test
        n = len(self.db)
        del self.db[1]
        assert len(self.db) == n - 1
        try:
            result = self.db[1]
            raise AssertionError('old ID still exists!')
        except KeyError:
            pass

    def test_setitem(self):
        'test assigning new ID to existing object'
        self.db.catchIter = True # no iter expected in this test
        o = self.db.new(id=17, seq_id='bob', start=2000, stop=2500)
        self.db[13] = o
        assert o.id == 13
        try:
            result = self.db[17]
            raise AssertionError('old ID still exists!')
        except KeyError:
            pass
        t = self.tableClass(self.tableName,
                            serverInfo=self.serverInfo) # requery the db
        t.catchIter = True # no iter expected in this test
        result = t[13]
        assert result.seq_id == 'bob' and result.start==2000 \
               and result.stop==2500
        try:
            result = t[17]
            raise AssertionError('old ID still exists!')
        except KeyError:
            pass


class SQLiteTableRW_Test(SQLiteBase, SQLTableRW_Test):
    pass


class SQLTableRW_NoCache_Test(SQLTableRW_Test):
    tableClass = SQLTableNoCache


class SQLiteTableRW_NoCache_Test(SQLiteTableRW_Test):
    tableClass = SQLTableNoCache


class Ensembl_Test(unittest.TestCase):

    def setUp(self):
        # test will be skipped if mysql module or ensembldb server unavailable

        logger.debug('accessing ensembldb.ensembl.org')
        conn = DBServerInfo(host='ensembldb.ensembl.org', user='anonymous',
                            passwd='')
        try:
            translationDB = \
                    SQLTableCatcher('homo_sapiens_core_47_36i.translation',
                                    serverInfo=conn)
            translationDB.catchIter = True # should not iter in this test!
            exonDB = SQLTable('homo_sapiens_core_47_36i.exon', serverInfo=conn)
        except ImportError, e:
            raise SkipTest(e)

        sql_statement = '''SELECT t3.exon_id FROM
homo_sapiens_core_47_36i.translation AS tr,
homo_sapiens_core_47_36i.exon_transcript AS t1,
homo_sapiens_core_47_36i.exon_transcript AS t2,
homo_sapiens_core_47_36i.exon_transcript AS t3 WHERE tr.translation_id = %s
AND tr.transcript_id = t1.transcript_id AND t1.transcript_id =
t2.transcript_id AND t2.transcript_id = t3.transcript_id AND t1.exon_id =
tr.start_exon_id AND t2.exon_id = tr.end_exon_id AND t3.rank >= t1.rank AND
t3.rank <= t2.rank ORDER BY t3.rank
            '''
        self.translationExons = GraphView(translationDB, exonDB,
                                          sql_statement, serverInfo=conn)
        self.translation = translationDB[15121]

    def test_orderBy(self):
        "Ensemble access, test order by"
        'test issue 53: ensure that the ORDER BY results are correct'
        exons = self.translationExons[self.translation] # do the query
        result = [e.id for e in exons]
        correct = [95160, 95020, 95035, 95050, 95059, 95069, 95081, 95088,
                   95101, 95110, 95172]
        self.assertEqual(result, correct) # make sure the exact order matches


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = megatest_utils
import BaseHTTPServer
import errno
import os
import mimetypes
import socket
import sys
import threading


class MinimalistHTTPServer(BaseHTTPServer.HTTPServer):
    'A HTTP server class to pass parameters to MinimalistHTTPRequestHandler'

    def set_file(self, allowed_file):
        'Prepare everything for serving our single available file.'
        # Avoid any funny business regarding the path, just in case.
        self.allowed_file = os.path.realpath(allowed_file)


class MinimalistHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    '''A minimalist request handler, to handle only GET requests
    for a single, specified file'''

    def do_GET(self):
        'Serve the specified file when requested, return errors otherwise'
        # The only request path to accept is '/self.server.allowed_file'.
        if self.path != '/' + os.path.basename(self.server.allowed_file):
            self.send_error(403)
            return

        try:
            fout = open(self.server.allowed_file)
        except IOError:
            self.send_error(404)
            return

        self.send_response(200)
        mimetypes.init()
        mime_guess = mimetypes.guess_type(self.server.allowed_file)
        if mime_guess[0] is not None:
            self.send_header('Content-Type', mime_guess[0])
        if mime_guess[1] is not None:
            self.send_header('Content-Encoding', mime_guess[1])
        statinfo = os.stat(self.server.allowed_file)
        self.send_header('Content-Length', statinfo.st_size)
        self.end_headers()
        try:
            self.wfile.write(fout.read())
        except socket.error, e:
            # EPIPE likely means the client's closed the connection,
            # it's nothing of concern so suppress the error message.
            if errno.errorcode[e[0]] == 'EPIPE':
                pass

        fout.close()
        return


class HTTPServerLauncher(object):
    'A launcher class for MinimalistHTTPServer.'

    def __init__(self, server_addr, file):
        self.server = MinimalistHTTPServer(server_addr,
                                           MinimalistHTTPRequestHandler)
        self.server.set_file(file)

    def request_shutdown(self):
        if sys.version_info >= (2, 6):
            self.server.shutdown()
        else:
            self.run_it = False

    def run(self):
        if sys.version_info >= (2, 6):
            # Safe to use here because 2.6 provides server.shutdown().
            self.server.serve_forever()
        else:
            self.run_it = True
            while self.run_it == True:
                # WARNING: if this blocks and no request arrives, the server
                # may remain up indefinitely! FIXME?
                self.server.handle_request()

########NEW FILE########
__FILENAME__ = pathfix
"""
The sole purpose of this module is to alter the sys.path upon
import in such a way to get pygr from the source directory rather than
@CTB finish comment?

See the README.txt file for details on how to change the behavior.

NOTE in place builds are required:

python setup.py build_ext -i
"""

import distutils.util
import platform
import os
import sys

import testoptions


def path_join(*args):
    "Joins and normalizes paths"
    return os.path.abspath(os.path.join(*args))


# we cannot use the main logger, because the import paths
# may not be set up yet
def info(msg):
    "Prints a message"
    sys.stderr.write(msg + '\n')


def stop(msg):
    "A fatal unrecoverable error"
    info(msg)
    sys.exit()

# get the current directory of the current module
curr_dir = os.path.dirname(__file__)

# this is the extra path that needs be added
base_dir = path_join(curr_dir, '..', '..')

# get the pygr source directory
pygr_source_dir = path_join(base_dir, 'pygr')

# build specific directories
os_info = distutils.util.get_platform()
version = ".".join([str(x) for x in platform.python_version_tuple()[:2]])
lib_dir = 'lib.%s-%s' % (os_info, version, )
temp_dir = 'temp.%s-%s' % (os_info, version, )
pygr_build_dir = path_join(base_dir, 'build', lib_dir)
pygr_temp_dir = path_join(base_dir, 'build', temp_dir)

# we'll do a top level option parsing in this module as well
parser = testoptions.option_parser()

# parse the arguments
options, args = parser.parse_args()

# this makes it less clunky
use_pathfix = not options.no_pathfix

# stores the error message about the import path
path_errmsg = None

if use_pathfix:
    # alter the import path
    if options.builddir:
        path_errmsg = "Importing pygr from platform build path %s" % \
                pygr_build_dir
        sys.path = [pygr_build_dir] + sys.path
        required_prefix = pygr_build_dir
    else:
        path_errmsg = "Importing pygr from source directory %s" % base_dir
        sys.path = [base_dir] + sys.path
        required_prefix = pygr_source_dir
    # For the sake of non-ambiguity
    required_prefix = os.path.realpath(required_prefix)
else:
    path_errmsg = "Importing pygr from default path"

###


# also, start coverage
def start_coverage():
    import figleaf
    from figleaf import annotate_html

    # Fix for figleaf misbehaving. It is adding a logger at root level
    # and that will add a handler to all subloggers (ours as well)
    # needs to be fixed in figleaf
    import logging
    root = logging.getLogger()

    # remove all root handlers
    for hand in root.handlers:
        root.removeHandler(hand)

    figleaf.start()

if options.coverage:
    start_coverage()

###

try:
    # try to import the main pygr module
    import pygr
    from pygr import logger

    # we have a logger now
    logger.info("importing pygr from %s" % pygr.__file__)

    # try to import an extension module
    from pygr import cnestedlist

except ImportError, exc:
    stop("""
    %s

    Error: '%s'

    Possible solutions:

        1. build the extension modules in place with:
                     python setup.py build_ext -i

        2. add the -b flag to runtest.py
                    (see runtest.py -h for more details)

        3. install a binary version of pygr into the system path

    """ % (path_errmsg, exc))

if use_pathfix:

    for mod in [pygr, cnestedlist]:
        # test that the imported python modules have the required prefix
        if not os.path.realpath(mod.__file__).startswith(required_prefix):
            stop("module %s imported from invalid path: %s" % \
                 (mod.__name__, os.path.realpath(mod.__file__)))

########NEW FILE########
__FILENAME__ = pygrdata_server
"""
Pygr XMLRPC server test. Recognized flags:

--port=PORT
    the port for the server

--port-file
    the filename to write the port info out to

--pygrdatapath=PYGRDATAPATH
    the pygr.Data directory

--resources=RESOURCE1:RESOURCE2:RESOURCE3
    a colon separated list of resource names

--downloadDB=DOWNLOADDB
    the shelve used

"""
import new
import os
import sys

import pathfix
import testoptions
import testutil
from pygr import logger
from pygr import metabase

# same options for all tests (some flags may be ignored)
parser = testoptions.option_parser()

# parse the arguments
options, args = parser.parse_args()

if options.pygrdatapath: # load from specified path
    mdb = metabase.MetabaseList(options.pygrdatapath)
else: # use default PYGRDATAPATH
    mdb = metabase.MetabaseList()


# disables debug messages at zero verbosity
if options.verbosity == 0:
    logger.disable('DEBUG')

# the resources are listed as colon separated names
names = filter(None, options.resources.split(':'))
resources = map(mdb, names) # load the specified resources

# set it to None by default
options.downloadDB = options.downloadDB or None

# create a new server that will serve the resources we just loaded
xmlrpc = metabase.ResourceServer(mdb, 'testy',
                                 withIndex=True,
                                 downloadDB=options.downloadDB,
                                 host='localhost', port=options.port)

# if needed, write out the port information to a file, so that the test runner
# can retrieve it.
if options.port_file:
    print 'writing port information to %s' % options.port_file
    fp = open(options.port_file, 'w')
    fp.write("%d" % (xmlrpc.port))
    fp.close()


# main loop
def serve_forever(self):
    self.keepRunning = True
    while self.keepRunning:
        self.handle_request()


# exit handler
def exit_now(self):
    self.keepRunning = False
    return 0

# add and exit handler to the server
exit_handler = new.instancemethod(exit_now, xmlrpc.server,
                                  xmlrpc.server.__class__)

# register exit handler
xmlrpc.server.register_function(exit_handler)

# starts the server and never returns...
print 'running server on %s:%s' % (xmlrpc.host, xmlrpc.port)
serve_forever(xmlrpc.server)

########NEW FILE########
__FILENAME__ = testoptions
"""
Option parser for all tests

Needs to be a separate module to avoid circular imports
"""

import optparse
import sys


def option_parser():
    """
    Returns the option parser for tests.

    This parser needs to be able to handle all flags that may be passed
    to any test

    Due to the optparse desing we cannot create a 'partial' option parser
    that would ignore extra parameters while allowing it to be later be
    extended. So it is either every flag goes the main option parser,
    or each module will have to implement almost identical parsers.

    Having one large option parser seemed the lesser of two bad choices.
    """

    parser = optparse.OptionParser()

    # passing -n will disable the pathfix, use it to test global pygr
    # distributions
    parser.add_option(
        '-n', '--nopath', action="store_true", dest="no_pathfix",
        default=False, help="do not alter the python import path")

    # add the regular build directory rather than the in place directory
    parser.add_option(
        '-b', '--buildpath', action="store_true", dest="builddir",
        default=False, help="use the platform specific build directory",
    )

    # stops testing immediately after a test suite fails
    parser.add_option(
        '-s', '--strict', action="store_true",
        dest="strict", default=False,
        help="stops testing after a test suite fails")

    # exclude the modules listed in arguments from all the tests
    parser.add_option(
        '-x', '--exclude', action="store_true",
        dest="exclude", default=False,
        help="excludes the files that are listed")

    # verbosity can be 0,1 and 2 (increasing verbosity)
    parser.add_option(
        '-v', '--verbosity', action="store",
        dest="verbosity", type="int", default=0,
        help="sets the verbosity (0, 1, or 2)",
    )

    # long options are typically used only within individual tests

    # executes figleaf to collect the coverage data
    parser.add_option(
        '--coverage', action="store_true", dest="coverage", default=False,
        help=
  "runs figleaf and collects the coverage information into the html directory")

    # adds the clean option to the testrunner
    parser.add_option(
        '--no-clean', action="store_false", dest="clean", default=True,
        help="does not reset the temporary directory and temp files")

    # runs the performance tests
    parser.add_option(
        '--performance', action="store_true", dest="performance",
        default=False,
        help="runs the performance tests (not implemented)")

    # port information for the pygrdata_test.py test; default is random
    parser.add_option(
        '--port', action="store", type="int",
        dest="port", default=0,
        help="sets the port information for the XMLRPC server")

    # where to write out the port information, for communication to test
    # runner.
    parser.add_option(
        '--port-file', action="store", type="string",
        dest="port_file",
        help="where to write the port information for the XMLRPC server")

    # set the pygraphdata path from command line
    parser.add_option(
        '--pygrdatapath', action="store", type="string",
        dest="pygrdatapath", default='',
        help="sets the pygraphdata path for the XMLRPC server")

    # add resources to the path colon separated
    # --downloadDB=database1
    parser.add_option(
        '--downloadDB', action="store", type="string",
        dest="downloadDB", default=None,
        help="sets the downloadDB shelve for the XMLRPC server")


    # add resources to the path colon separated
    # --resources=database1
    parser.add_option('--resources', action="store", type="string",
                      dest="resources", default='',
                      help=
     "sets the downloadable resources, separate multiple ones with a : symbol")

    return parser

if __name__ == '__main__':
    # list flags here
    flags = " --downloadDB=1234 "

    sys.argv.extend(flags.split())
    parser = option_parser()
    options, args = parser.parse_args()

    print options

########NEW FILE########
__FILENAME__ = testutil
"""
Utility functions for testing
"""

import atexit
import glob
import os
import random
import re
import shutil
import sys
import threading
import time
import unittest
import warnings
import tempfile as tempfile_mod

from unittest_extensions import SkipTest

import pathfix
from pygr import logger, classutil

try:
    import hashlib
except ImportError:
    import md5 as hashlib


# represents a test data
class TestData(object):
    pass

# a shortcut
path_join = pathfix.path_join

# use the main logger to produce
info, error, warn, debug = logger.info, logger.error, logger.warn, logger.debug

# global port setting
default_xmlrpc_port = 0              # 0 -> random port; overriden by runtest.

###


def approximate_cmp(x, y, delta):
    '''expects two lists of tuples.  Performs comparison as usual,
    except that numeric types are considered equal if they differ by
    less than delta'''
    diff = cmp(len(x), len(y))
    if diff != 0:
        return diff
    x.sort() # SORT TO ENSURE IN SAME ORDER...
    y.sort()
    for i in range(len(x)):
        s = x[i]
        t = y[i]
        diff = cmp(len(s), len(t))
        if diff != 0:
            return diff
        for j in range(len(s)):
            u = s[j]
            v = t[j]
            if isinstance(u, int) or isinstance(u, float):
                diff = u - v
                if diff < -delta:
                    return -1
                elif diff >delta:
                    return 1
            else:
                diff = cmp(u, v)
                if diff != 0:
                    return diff
    return 0


def stop(text):
    "Unrecoverable error"
    logger.error(text)
    sys.exit()


def change_pygrdatapath(*args):
    "Overwrites the PYGRDATAPATH enviroment variable (local copy)"
    path = path_join(*args)
    if not os.path.isdir(path):
        stop('cannot access pygrdatapath %s' % path)
    os.environ['PYGRDATAPATH'] = path
    os.environ['PYGRDATADOWNLOAD'] = path
    import pygr.Data


def generate_coverage(func, path, *args, **kwds):
    """
    Generates code coverage for the function
    and places the results in the path
    """
    import figleaf
    from figleaf import annotate_html

    if os.path.isdir(path):
        shutil.rmtree(path)

    # execute the function itself
    return_vals = func(*args, **kwds)

    logger.info('generating coverage')
    coverage = figleaf.get_data().gather_files()
    annotate_html.prepare_reportdir(path)

    # skip python modules and the test modules
    regpatt = lambda patt: re.compile(patt, re.IGNORECASE)
    patterns = map(regpatt, ['python', 'tests'])
    annotate_html.report_as_html(coverage, path, exclude_patterns=patterns,
                                 files_list='')

    return return_vals


class TempDir(object):
    """
    Returns a directory in the temporary directory, either named or a
    random one
    """

    def __init__(self, prefix, path='tempdir'):
        self.prefix = prefix
        self.tempdir = path_join(pathfix.curr_dir, '..', path)
        self.path = self.get_path()
        atexit.register(self.remove)

    def reset(self):
        "Resets the root temporary directory"

        logger.debug('resetting path %s' % self.tempdir)
        shutil.rmtree(self.path, ignore_errors=True)
        shutil.rmtree(self.tempdir, ignore_errors=True)
        self.path = self.get_path()

    def get_path(self):
        if not os.path.isdir(self.tempdir):
            os.mkdir(self.tempdir)
        path = tempfile_mod.mkdtemp(prefix=self.prefix, dir=self.tempdir)
        return path

    def randname(self, prefix='x'):
        "Generates a random name"
        id = prefix + str(random.randint(0, 2**31))
        return id

    def subfile(self, name=None):
        """
        Returns a path to a file in the temporary directory,
        either the named or a random one
        """
        name = name or self.randname(prefix='f')
        return path_join(self.path, name)

    def remove(self):
        "Removes the temporary directory"
        #shutil.rmtree(self.path, ignore_errors=True)
        pass


class TestXMLRPCServer(object):
    """
    Runs XMLRPC server in the background with a list of pygr.Data resources
    Makes server exit when this object is released. Because we want this to
    work even on Windows, we can't use fork, backgrounding or any other
    quasi-sensible method for running the server process in the background.
    So we just use a separate thread to keep our caller from blocking...

    Optional arguments:
    PYGRDATAPATH: passed to the server process command line as its PYGRDATAPATH
    checkResources: if True, first check that all pygrDataNames are loadable.
    """

    def __init__(self, pygrDataNames, pygrDataPath, port=0, downloadDB=''):
        'starts server, returns without blocking'
        self.pygrDataNames = pygrDataNames
        self.pygrDataPath = pygrDataPath
        self.downloadDB = downloadDB

        global default_xmlrpc_port
        if not port:
            port = default_xmlrpc_port

        self.port = port
        self.port_file = tempdatafile('xmlrpc_port_file', False)

        # check that all resources are available
        ## if kwargs.get('checkResources'):
        ##     map(pygr.Data.getResource, *pygrDataNames)

        currdir = os.path.dirname(__file__)
        self.server_script = path_join(currdir, 'pygrdata_server.py')

        # start the thread
        self.thread = threading.Thread(target=self.run_server)
        self.thread.start()

        port = None
        for i in range(10): # retry several times in case server starts slowly
            # wait for it to start
            time.sleep(1)
            # retrieve port info from file saved by server
            try:
                ifile = open(self.port_file)
                try:
                    port = int(ifile.read())
                    break # exit the loop
                finally:
                    ifile.close() # make sure to close file no matter what
            except IOError:
                pass
        assert port, "cannot get port info from server; is server running?"
        self.port = port # use the port returned by the server

    def run_server(self):
        'this method blocks, so run it in a separate thread'
        cmdArgs = (sys.executable, self.server_script) + tuple(sys.argv) \
                  + ('--port-file=' + self.port_file,
                     '--pygrdatapath=' + self.pygrDataPath,
                     '--downloadDB=' + self.downloadDB,
                     '--resources=' + ':'.join(self.pygrDataNames))
        if self.port: # only add port argument if set
            cmdArgs += ('--port=' + str(self.port), )
        p = classutil.FilePopen(cmdArgs, stdout=classutil.PIPE,
                                stderr=classutil.PIPE)
        try:
            logger.debug('Starting XML-RPC server: ')
            logger.debug(repr(cmdArgs))
            if p.wait():
                logger.warn('XML-RPC server command failed!')
            output = p.stdout.read()
            errout = p.stderr.read()
            logger.debug('XML-RPC server output: %s' % output)
            logger.debug('XML-RPC server error out: %s' % errout)
        finally:
            p.close()

        logger.debug('server stopped')

    def close(self):
        import xmlrpclib
        s = xmlrpclib.ServerProxy('http://localhost:%d' % self.port)
        s.exit_now() # TELL THE SERVER TO EXIT

        self.thread.join()


def make_suite(tests):
    "Makes a test suite from a list of TestCase classes"
    loader = unittest.TestLoader().loadTestsFromTestCase
    suites = map(loader, tests)
    return unittest.TestSuite(suites)


def mysql_enabled():
    """
    Detects whether mysql is functional on the current system
    """
    try:
        import MySQLdb
    except ImportError, exc:
        msg = 'MySQLdb error: %s' % exc
        warn(msg)
        return False
    try:
        from pygr import sqlgraph
        tempcurs = sqlgraph.get_name_cursor()[1]
        # disable some MySQL specific spurious warnings, current scope only
        warnings.simplefilter("ignore")
        tempcurs.execute('create database if not exists test')
    except Exception, exc:
        msg = 'cannot operate on MySql database: %s' % exc
        warn(msg)
        return False

    return True


def sqlite_enabled():
    """
    Detects whether sqlite3 is functional on the current system
    """
    from pygr.sqlgraph import import_sqlite
    try:
        sqlite = import_sqlite() # from 2.5+ stdlib, or pysqlite2
    except ImportError, exc:
        msg = 'sqlite3 error: %s' % exc
        warn(msg)
        return False
    return True


class SQLite_Mixin(object):
    'use this as a base for any test'

    def setUp(self):
        from pygr.sqlgraph import SQLiteServerInfo
        if not sqlite_enabled():
            raise SkipTest
        self.sqlite_file = tempdatafile('test_sqlite.db', False)
        self.tearDown(False) # delete the file if it exists
        self.serverInfo = SQLiteServerInfo(self.sqlite_file)
        self.sqlite_load() # load data provided by subclass method

    def tearDown(self, closeConnection=True):
        'delete the sqlite db file after (optionally) closing connection'
        if closeConnection:
            self.serverInfo.close() # close the database
        try:
            os.remove(self.sqlite_file)
        except OSError:
            pass


def temp_table_name(dbname='test'):
    import random
    l = [c for c in 'TeMpBiGdAcDy']
    random.shuffle(l)
    return dbname+'.'+''.join(l)


def drop_tables(cursor, tablename):
    cursor.execute('drop table if exists %s' % tablename)
    cursor.execute('drop table if exists %s_schema' % tablename)

_blast_enabled = None                  # cache results of blast_enabled()


def blast_enabled():
    """
    Detects whether the blast suite is functional on the current system
    """
    global _blast_enabled
    if _blast_enabled is not None:
        return _blast_enabled

    p = classutil.FilePopen(('blastall', ), stdout=classutil.PIPE)
    try:
        p.wait() # try to run the program
    except OSError:
        warn('NCBI toolkit (blastall) missing?')
        _blast_enabled = False
        return False
    p.close()

    _blast_enabled = True
    return True

###


DATADIR = path_join(pathfix.curr_dir, '..', 'data')
TEMPROOT = TempDir('tempdir')
TEMPDIR = TEMPROOT.path

# shortcuts for creating full paths to files in the data and temporary
# directories
datafile = lambda name: path_join(DATADIR, name)


def tempdatafile(name, errorIfExists=True, copyData=False):
    filepath = path_join(TEMPDIR, name)
    if errorIfExists and os.path.exists(filepath):
        raise AssertionError('tempdatafile %s already exists!' % name)
    if copyData: # copy data file to new location
        shutil.copyfile(datafile(name), filepath)
    return filepath


def remove_files(path, patterns=["*.seqlen"]):
    "Removes files matching any pattern in the list"
    for patt in patterns:
        fullpatt = path_join(path, patt)
        for name in glob.glob(fullpatt):
            os.remove(name)


def get_file_md5(fpath):
    ifile = file(fpath, 'rb')
    try:
        h = hashlib.md5(ifile.read())
    finally:
        ifile.close()
    return h


if __name__ == '__main__':
    t = TempDir('tempdir')
    t.reset()

    #TestXMLRPCServer()

########NEW FILE########
__FILENAME__ = unittest_extensions
"""
Provide support for test skipping.
"""

import unittest
from pygr import logger


try:
    from nose.plugins.skip import SkipTest
except ImportError: # no nose?

    class SkipTest(Exception):
        pass


class PygrTestResult(unittest._TextTestResult):

    def __init__(self, *args, **kwargs):
        unittest._TextTestResult.__init__(self, *args, **kwargs)
        self.skipped = []

        # by default, support dots at lowest verbosity.
        verbosity = kwargs.get('verbosity', 0)
        show_dots = kwargs.get('show_dots', 1)
        if verbosity == 0 and show_dots:
            self.dots = 1

    def addError(self, test, err):
        exc_type, val, _ = err
        if issubclass(exc_type, SkipTest):
            self.skipped.append((self, val))
            if self.showAll:                         # report skips: SKIP/S
                self.stream.writeln("SKIP")
            elif self.dots:
                self.stream.write('S')
        else:
            unittest._TextTestResult.addError(self, test, err)


class PygrTestRunner(unittest.TextTestRunner):
    """
    Support running tests that understand SkipTest.
    """

    def _makeResult(self):
        return PygrTestResult(self.stream, self.descriptions,
                              self.verbosity)


class PygrTestProgram(unittest.TestProgram):

    def __init__(self, **kwargs):
        verbosity = kwargs.pop('verbosity', 1)
        if verbosity < 1:
            logger.disable('INFO')  # Should implicity disable DEBUG as well
        elif verbosity < 2:
            logger.disable('DEBUG')
        if kwargs.get('testRunner') is None:
            kwargs['testRunner'] = PygrTestRunner(verbosity=verbosity)

        unittest.TestProgram.__init__(self, **kwargs)

########NEW FILE########
__FILENAME__ = send_megatest_email
#!/usr/bin/env python

import ConfigParser
import os
import smtplib
import time
try:
    from email.mime.text import MIMEText
except ImportError:
    from email.MIMEText import MIMEText


def extract_errors(text):
    errors = []
    start_line = -1
    for idx, line in enumerate(text):
        if line[:6] == 'ERROR:':
            start_line = idx - 1
        elif line == '\n' and start_line >= 0:
            for i in range(start_line, idx + 1):
                errors.append(text[i])
            start_line = -1

    return errors


config = ConfigParser.ConfigParser({'expectedRunningTime': '-1',
                                    'mailServer': '',
                                    'runningTimeAllowedDelay': '0'})
config.read([os.path.join(os.path.expanduser('~'), '.pygrrc'),
             os.path.join(os.path.expanduser('~'), 'pygr.cfg'),
             '.pygrrc', 'pygr.cfg'])
expectedRunningTime = config.get('megatests', 'expectedRunningTime')
logdir = config.get('megatests', 'logDir')
mailsender = config.get('megatests', 'mailFrom')
mailserver = config.get('megatests', 'mailServer')
maillist_fail = config.get('megatests', 'mailTo_failed')
maillist_pass = config.get('megatests', 'mailTo_ok')
runningTimeAllowedDelay = config.get('megatests', 'runningTimeAllowedDelay')

timeStr = time.ctime()
dateStr = ' '.join([ix for ix in timeStr.split(' ') if ':' not in ix])

# Gather the runner script's output
os.chdir(logdir)
sendStr = 'MEGATEST report, generated ' + timeStr + '\n\n'
sendStr += 'Test started: ' + open('tmp1_megatest.log', 'r').readlines()[0]
sendStr += 'PYTHONPATH = ' + open('tmp3_megatest.log', 'r').read() + '\n'
sendStr += 'Output of standard tests:\n' + ''.join(open('tmp2_megatest.log',
                                                       'r').readlines()[-5:]) \
        + '\n\n'
sendStr += 'Output of megatests:\n' + ''.join(open('tmp4_megatest.log',
                                                   'r').readlines()[-5:]) \
        + '\n\n'
sendStr += 'Test finished: ' + open('tmp5_megatest.log', 'r').readlines()[0] \
        + '\n'

# Try to determine whether the test has failed or not
nError = 0
abnormalStop = 0

# Compare running time with expectations, mark test as failed if it took
# significantly longer than it should (some latitude is given to account
# for fluctuations due to machine/network/... load).
# Unlike later on, increment abnormalStop first and decrement it in case
# of failure - it's cleaner than the other way around.
abnormalStop += 1
expectedRunningTime = float(expectedRunningTime)
if expectedRunningTime >= 0.:
    startTime = int(open('tmp1_megatest.log',
                         'r').readlines()[1].split(':')[1].strip())
    endTime = int(open('tmp5_megatest.log',
                       'r').readlines()[1].split(':')[1].strip())
    if runningTimeAllowedDelay[-1] == '%':
        maxRunningTime = expectedRunningTime * \
                (1 + float(runningTimeAllowedDelay[:-1]) / 100.)
    else:
        maxRunningTime = expectedRunningTime + float(runningTimeAllowedDelay)
    runMinutes = (endTime - startTime) / 60.
    if runMinutes > maxRunningTime:
        sendStr += '\n' + '#' * 69 + '\n'
        sendStr += \
          'ERROR: megatests took %s minutes to complete, expected %s minutes' \
                % (runMinutes, expectedRunningTime)
        sendStr += '\n' + '#' * 69 + '\n'
        abnormalStop -= 1

for lines in sendStr.splitlines():
    if lines[:4] == 'INFO' and 'passed' in lines and 'failed' in lines and \
       'skipped' in lines:
        nError += int(lines[18:].split(',')[1].strip().split(' ')[0])
        abnormalStop += 1

if nError > 0:
    sendStr += '\nThe following errors have been detected:\n'
    sendStr += ''.join(extract_errors(open('tmp2_megatest.log',
                                           'r').readlines()))
    sendStr += ''.join(extract_errors(open('tmp4_megatest.log',
                                           'r').readlines()))

if nError == 0 and abnormalStop == 3:
    maillist = maillist_pass
else:
    maillist = maillist_fail

# Create and send the message
msg = MIMEText(sendStr)
msg['From'] = mailsender
msg['To'] = maillist
msg['Subject'] = 'Megatest on ' + dateStr + ' with ' + str(nError) + ' Errors'
s = smtplib.SMTP(mailserver)
s.connect()
s.sendmail(mailsender, maillist.replace(',', ' ').split(), msg.as_string())
s.close()

########NEW FILE########
__FILENAME__ = translationDB_test
import unittest

from testlib import testutil, PygrTestProgram
from pygr import translationDB, seqdb


class TranslationDB_Test(unittest.TestCase):

    def setUp(self):
        hbb1_mouse = testutil.datafile('hbb1_mouse.fa')
        self.dna = seqdb.SequenceFileDB(hbb1_mouse)
        self.tdb = translationDB.get_translation_db(self.dna)

    def test_basic_slice(self):
        id = 'gi|171854975|dbj|AB364477.1|'
        tseq = self.tdb[id][0:99]
        assert str(tseq)[0:10] == 'MVHLTDAEKA'

        tseq = self.tdb[id][1:100]
        assert str(tseq)[0:10] == 'WCT*LMLRRL'

    def test_slice_empty_stop(self):
        id = 'gi|171854975|dbj|AB364477.1|'
        tseq = self.tdb[id][0:]
        assert str(tseq)[0:10] == 'MVHLTDAEKA'

        tseq = self.tdb[id][1:]
        assert str(tseq)[0:10] == 'WCT*LMLRRL'

    def test_slice_empty_start(self):
        id = 'gi|171854975|dbj|AB364477.1|'
        tseq = self.tdb[id][:99]
        assert str(tseq)[0:10] == 'MVHLTDAEKA'

    def test_repr_ne(self):
        """
        Make sure there's some way to distinguish translated seqs from
        regular, visually!
        """
        id = 'gi|171854975|dbj|AB364477.1|'

        seq = self.dna[id]
        tseq = self.tdb[id]

        assert repr(seq) != repr(tseq)

    def test_invalid_annodb_key_str(self):
        """
        The invalid key should be mentioned in the KeyError...
        """
        try:
            self.tdb.annodb['fooBar']
            assert 0, "should not reach this point"
        except KeyError, e:
            assert 'fooBar' in str(e)

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
__FILENAME__ = worldbase_test
import datetime
import md5
import os
import pickle
import socket
import unittest

import testlib
from testlib import testutil, SkipTest, PygrTestProgram
from pygr import seqdb, cnestedlist, metabase, mapping
from pygr import worldbase
from pygr.downloader import SourceURL, GenericBuilder

try:
    set
except NameError:
    from sets import Set as set


class TestBase(unittest.TestCase):
    "A base class to all worldbase test classes"

    def setUp(self, worldbasePath=None, **kwargs):
        # overwrite the WORLDBASEPATH environment variable
        self.tempdir = testutil.TempDir('pygrdata')
        if worldbasePath is None:
            worldbasePath = self.tempdir.path
        worldbase.update(worldbasePath, **kwargs)
        # handy shortcuts
        self.EQ = self.assertEqual


class Download_Test(TestBase):
    "Save seq db and interval to worldbase shelve"

    # tested elsewhere as well, on Linux makes gzip ask for permissions
    # to overwrite
    def test_download(self):
        "Downloading of gzipped file using worldbase"

        url = SourceURL('http://www.doe-mbi.ucla.edu/~leec/test.gz')
        url.__doc__ = 'test download'

        worldbase.add_resource('Bio.Test.Download1', url)
        worldbase.commit()

        # performs the download
        fpath = worldbase.Bio.Test.Download1()
        h = testutil.get_file_md5(fpath)
        self.assertEqual(h.hexdigest(), 'f95656496c5182d6cff9a56153c9db73')
        os.remove(fpath)


class GenericBuild_Test(TestBase):

    def test_generic_build(self):
        "GenericBuilder construction of the BlastDB"

        sp_hbb1 = testutil.datafile('sp_hbb1')
        gb = GenericBuilder('BlastDB', sp_hbb1)
        s = pickle.dumps(gb)
        db = pickle.loads(s) # force construction of the BlastDB
        self.EQ(len(db), 24)

        found = [x for x in db]
        found.sort()

        expected = ['HBB0_PAGBO', 'HBB1_ANAMI', 'HBB1_CYGMA', 'HBB1_IGUIG',
                   'HBB1_MOUSE', 'HBB1_ONCMY', 'HBB1_PAGBO', 'HBB1_RAT',
                   'HBB1_SPHPU', 'HBB1_TAPTE', 'HBB1_TORMA', 'HBB1_TRICR',
                   'HBB1_UROHA', 'HBB1_VAREX', 'HBB1_XENBO', 'HBB1_XENLA',
                   'HBB1_XENTR', 'MYG_DIDMA', 'MYG_ELEMA', 'MYG_ERIEU',
                   'MYG_ESCGI', 'MYG_GALCR', 'PRCA_ANASP', 'PRCA_ANAVA']
        expected.sort()

        self.EQ(expected, found)


class DNAAnnotation_Test(TestBase):

    def setUp(self, **kwargs):
        TestBase.setUp(self)
        dnaseq = testutil.datafile('dnaseq.fasta')
        tryannot = testutil.tempdatafile('tryannot')

        db = seqdb.BlastDB(dnaseq)
        try:
            db.__doc__ = 'little dna'

            worldbase.Bio.Test.dna = db
            annoDB = seqdb.AnnotationDB({1: ('seq1', 5, 10, 'fred'),
                                         2: ('seq1', -60, -50, 'bob'),
                                         3: ('seq2', -20, -10, 'mary')},
                                        db,
                                  sliceAttrDict=dict(id=0, start=1, stop=2,
                                                     name=3))
            annoDB.__doc__ = 'trivial annotation'
            worldbase.Bio.Test.annoDB = annoDB
            nlmsa = cnestedlist.NLMSA(tryannot, 'w', pairwiseMode=True,
                                      bidirectional=False)
            try:
                for annID in annoDB:
                    nlmsa.addAnnotation(annoDB[annID])

                nlmsa.build()
                nlmsa.__doc__ = 'trivial map'
                worldbase.Bio.Test.map = nlmsa
                worldbase.schema.Bio.Test.map = metabase.ManyToManyRelation(db,
                                                annoDB, bindAttrs=('exons', ))
                worldbase.commit()
                worldbase.clear_cache()
            finally:
                nlmsa.close()
        finally:
            db.close()

    def test_annotation(self):
        "Annotation test"
        db = worldbase.Bio.Test.dna()
        try:
            s1 = db['seq1']
            l = s1.exons.keys()
            annoDB = worldbase.Bio.Test.annoDB()
            assert l == [annoDB[1], -(annoDB[2])]
            assert l[0].sequence == s1[5:10]
            assert l[1].sequence == s1[50:60]
            assert l[0].name == 'fred', 'test annotation attribute access'
            assert l[1].name == 'bob'
            sneg = -(s1[:55])
            l = sneg.exons.keys()
            assert l == [annoDB[2][5:], -(annoDB[1])]
            assert l[0].sequence == -(s1[50:55])
            assert l[1].sequence == -(s1[5:10])
            assert l[0].name == 'bob'
            assert l[1].name == 'fred'
        finally:
            db.close() # close SequenceFileDB
            worldbase.Bio.Test.map().close() # close NLMSA


def populate_swissprot():
    "Populate the current worldbase with swissprot data"
    # build BlastDB out of the sequences
    sp_hbb1 = testutil.datafile('sp_hbb1')
    sp = seqdb.BlastDB(sp_hbb1)
    sp.__doc__ = 'little swissprot'
    worldbase.Bio.Seq.Swissprot.sp42 = sp

    # also store a fragment
    hbb = sp['HBB1_TORMA']
    ival= hbb[10:35]
    ival.__doc__ = 'fragment'
    worldbase.Bio.Seq.frag = ival

    # build a mapping to itself
    m = mapping.Mapping(sourceDB=sp, targetDB=sp)
    trypsin = sp['PRCA_ANAVA']
    m[hbb] = trypsin
    m.__doc__ = 'map sp to itself'
    worldbase.Bio.Seq.spmap = m

    # create an annotation database and bind as exons attribute
    worldbase.schema.Bio.Seq.spmap = metabase.OneToManyRelation(sp, sp,
                                                         bindAttrs=('buddy', ))
    annoDB = seqdb.AnnotationDB({1: ('HBB1_TORMA', 10, 50)}, sp,
                                sliceAttrDict=dict(id=0, start=1, stop=2))
    exon = annoDB[1]

    # generate the names where these will be stored
    tempdir = testutil.TempDir('exonAnnot')
    filename = tempdir.subfile('cnested')
    nlmsa = cnestedlist.NLMSA(filename, 'w', pairwiseMode=True,
                              bidirectional=False)
    nlmsa.addAnnotation(exon)
    nlmsa.build()
    annoDB.__doc__ = 'a little annotation db'
    nlmsa.__doc__ = 'a little map'
    worldbase.Bio.Annotation.annoDB = annoDB
    worldbase.Bio.Annotation.map = nlmsa
    worldbase.schema.Bio.Annotation.map = \
         metabase.ManyToManyRelation(sp, annoDB, bindAttrs=('exons', ))


def check_match(self):
    frag = worldbase.Bio.Seq.frag()
    correct = worldbase.Bio.Seq.Swissprot.sp42()['HBB1_TORMA'][10:35]
    assert frag == correct, 'seq ival should match'
    assert frag.__doc__ == 'fragment', 'docstring should match'
    assert str(frag) == 'IQHIWSNVNVVEITAKALERVFYVY', 'letters should match'
    assert len(frag) == 25, 'length should match'
    assert len(frag.path) == 142, 'length should match'

    #store = PygrDataTextFile('results/seqdb1.pickle')
    #saved = store['hbb1 fragment']
    #assert frag == saved, 'seq ival should matched stored result'


def check_dir(self):
    expected=['Bio.Annotation.annoDB', 'Bio.Annotation.map',
                'Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap']
    expected.sort()
    found = worldbase.dir('Bio')
    found.sort()
    assert found == expected


def check_dir_noargs(self):
    found = worldbase.dir()
    found.sort()
    found2 = worldbase.dir('')
    found2.sort()
    assert found == found2


def check_dir_download(self):
    found = worldbase.dir(download=True)
    found.sort()
    found2 = worldbase.dir('', download=True)
    found2.sort()
    assert len(found) == 0
    assert found == found2


def check_dir_re(self):
    expected=['Bio.Annotation.annoDB', 'Bio.Annotation.map',
                'Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap']
    expected.sort()
    found = worldbase.dir('^Bio', 'r')
    found.sort()
    assert found == expected

    expected = ['Bio.Seq.Swissprot.sp42', 'Bio.Seq.spmap']
    expected.sort()
    found = worldbase.dir('^Bio\..+\.sp', 'r')
    found.sort()
    assert found == expected


def check_bind(self):
    sp = worldbase.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    trypsin = sp['PRCA_ANAVA']
    assert hbb.buddy == trypsin, 'automatic schema attribute binding'


def check_bind2(self):
    sp = worldbase.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    exons = hbb.exons.keys()
    assert len(exons)==1, 'number of expected annotations'
    annoDB = worldbase.Bio.Annotation.annoDB()
    exon = annoDB[1]
    assert exons[0] == exon, 'test annotation comparison'
    assert exons[0].pathForward is exon, 'annotation parent match'
    assert exons[0].sequence == hbb[10:50], 'annotation to sequence match'
    onc = sp['HBB1_ONCMY']
    try:
        exons = onc.exons.keys()
        raise ValueError('failed to catch query with no annotations')
    except KeyError:
        pass


class Sequence_Test(TestBase):

    def setUp(self, *args, **kwargs):
        TestBase.setUp(self, *args, **kwargs)
        populate_swissprot()
        worldbase.commit() # finally save everything
        worldbase.clear_cache() # force all requests to reload

    def test_match(self):
        "Test matching sequences"
        check_match(self)

    def test_dir(self):
        "Test labels"
        check_dir(self)
        check_dir_noargs(self)
        check_dir_re(self)

    def test_bind(self):
        "Test bind"
        check_bind(self)
        check_bind2(self)

    def test_schema(self):
        "Test schema"
        sp_hbb1 = testutil.datafile('sp_hbb1')
        sp2 = seqdb.BlastDB(sp_hbb1)
        sp2.__doc__ = 'another sp'
        worldbase.Bio.Seq.sp2 = sp2
        sp = worldbase.Bio.Seq.Swissprot.sp42()
        m = mapping.Mapping(sourceDB=sp, targetDB=sp2)
        m.__doc__ = 'sp -> sp2'
        worldbase.Bio.Seq.testmap = m
        worldbase.schema.Bio.Seq.testmap = metabase.OneToManyRelation(sp, sp2)
        worldbase.commit()

        worldbase.clear_cache()

        sp3 = seqdb.BlastDB(sp_hbb1)
        sp3.__doc__ = 'sp number 3'
        worldbase.Bio.Seq.sp3 = sp3
        sp2 = worldbase.Bio.Seq.sp2()
        m = mapping.Mapping(sourceDB=sp3, targetDB=sp2)
        m.__doc__ = 'sp3 -> sp2'
        worldbase.Bio.Seq.testmap2 = m
        worldbase.schema.Bio.Seq.testmap2 = metabase.OneToManyRelation(sp3,
                                                                       sp2)
        l = worldbase._mdb.resourceCache.keys()
        l.sort()
        assert l == ['Bio.Seq.sp2', 'Bio.Seq.sp3', 'Bio.Seq.testmap2']
        worldbase.commit()
        g = worldbase._mdb.writer.storage.graph
        expected = set(['Bio.Annotation.annoDB',
                     'Bio.Seq.Swissprot.sp42', 'Bio.Seq.sp2', 'Bio.Seq.sp3'])
        found = set(g.keys())
        self.EQ(len(expected - found), 0)


class SQL_Sequence_Test(Sequence_Test):

    def setUp(self):
        if not testutil.mysql_enabled():
            raise SkipTest("no MySQL installed")

        self.dbtable = testutil.temp_table_name() # create temp db tables
        Sequence_Test.setUp(self, worldbasePath='mysql:' + self.dbtable,
                            mdbArgs=dict(createLayer='temp'))

    def tearDown(self):
        testutil.drop_tables(worldbase._mdb.writer.storage.cursor,
                             self.dbtable)


class InvalidPickle_Test(TestBase):

    def setUp(self):
        TestBase.setUp(self)

        class MyUnpicklableClass(object):
            pass

        MyUnpicklableClass.__module__ = '__main__'
        self.bad = MyUnpicklableClass()

        self.good = datetime.datetime.today()

    def test_invalid_pickle(self):
        "Testing an invalid pickle"
        s = metabase.dumps(self.good) # should pickle with no errors
        try:
            s = metabase.dumps(self.bad) # should raise exception
            msg = 'failed to catch bad attempt to invalid module ref'
            raise ValueError(msg)
        except metabase.WorldbaseNoModuleError:
            pass


class XMLRPC_Test(TestBase):
    'create an XMLRPC server and access seqdb from it'

    def setUp(self):
        TestBase.setUp(self)
        populate_swissprot() # save some data
        worldbase.commit() # finally save everything to metabase
        worldbase.clear_cache() # force all requests to reload

        res = ['Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap',
               'Bio.Annotation.annoDB', 'Bio.Annotation.map']
        self.server = testutil.TestXMLRPCServer(res, self.tempdir.path)

    def test_xmlrpc(self):
        "Test XMLRPC"
        worldbase.clear_cache() # force all future requests to reload
        # Add our test XMLRPC resource.
        worldbase.update("http://localhost:%s" % self.server.port)

        check_match(self) # run all our tests
        check_dir(self)
        check_dir_noargs(self)
        check_dir_download(self)
        check_dir_re(self)
        check_bind(self)
        check_bind2(self)

        sb_hbb1 = testutil.datafile('sp_hbb1') # test readonly checks
        sp2 = seqdb.BlastDB(sb_hbb1)
        sp2.__doc__ = 'another sp'
        try:
            worldbase.Bio.Seq.sp2 = sp2
            worldbase.commit()
            msg = 'failed to catch bad attempt to write to XMLRPC server'
            raise KeyError(msg)
        except ValueError:
            pass

    def tearDown(self):
        'halt the test XMLRPC server'
        self.server.close()


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

########NEW FILE########
