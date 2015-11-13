__FILENAME__ = annotate
import sys
import os
from cruzdb.models import Feature, ABase
from toolshed import reader, nopen

def _annotate(args):
    print args
    try:
        return annotate(*args)
    except:
        print >>sys.stderr, args
        raise

def _split_chroms(fname):
    import tempfile
    t = tempfile.mktemp(dir="/tmp", suffix=".cruzdb")
    chroms = {}
    for d in reader(fname, header="ordered"):
        if not d['chrom'] in chroms:
            chroms[d['chrom']] = open(t + "." + d['chrom'], "w")
            print >> chroms[d['chrom']], "\t".join(d.keys())
        print >>chroms[d['chrom']], "\t".join(d.values())
    for k in chroms:
        chroms[k].close()
        chroms[k] = (chroms[k], chroms[k].name + ".anno")
    return chroms.items()

def annotate(g, fname, tables, feature_strand=False, in_memory=False,
        header=None, out=sys.stdout, _chrom=None, parallel=False):
    """
    annotate bed file in fname with tables.
    distances are integers for distance. and intron/exon/utr5 etc for gene-pred
    tables. if the annotation features have a strand, the distance reported is
    negative if the annotation feature is upstream of the feature in question
    if feature_strand is True, then the distance is negative if t
    """
    close = False
    if isinstance(out, basestring):
        out = nopen(out, "w")
        close = True


    if parallel:
        import multiprocessing
        import signal
        p = multiprocessing.Pool(initializer=lambda:
                                signal.signal(signal.SIGINT, signal.SIG_IGN))
        chroms = _split_chroms(fname)

        def write_result(fanno, written=[False]):
            for i, d in enumerate(reader(fanno, header="ordered")):
                if i == 0 and written[0] == False:
                    print >>out, "\t".join(d.keys())
                    written[0] = True
                print >>out, "\t".join(x if x else "NA" for x in d.values())
            os.unlink(fanno)
            os.unlink(fanno.replace(".anno", ""))

        for fchrom, (fout, fanno) in chroms:
            p.apply_async(annotate, args=(g.db, fout.name, tables, feature_strand, True,
                                 header, fanno, fchrom),
                                 callback=write_result)
        p.close()
        p.join()
        return out.name

    if isinstance(g, basestring):
        from . import Genome
        g = Genome(g)
    if in_memory:
        from . intersecter import Intersecter
        intersecters = [] # 1 per table.
        for t in tables:
            q = getattr(g, t) if isinstance(t, basestring) else t
            if _chrom is not None:
                q = q.filter_by(chrom=_chrom)
            table_iter = q #page_query(q, g.session)
            intersecters.append(Intersecter(table_iter))

    elif isinstance(fname, basestring) and os.path.exists(fname) \
            and sum(1 for _ in nopen(fname)) > 25000:
        print >>sys.stderr, "annotating many intervals, may be faster using in_memory=True"
    if header is None:
        header = []
    extra_header = []
    for j, toks in enumerate(reader(fname, header=False)):
        if j == 0 and not header:
            if not (toks[1] + toks[2]).isdigit():
                header = toks
        if j == 0:
            for t in tables:
                annos = (getattr(g, t) if isinstance(t, basestring) else t).first().anno_cols
                h = t if isinstance(t, basestring) else t._table.name if hasattr(t, "_table") else t.first()._table.name
                extra_header += ["%s_%s" % (h, a) for a in annos]

            if 0 != len(header):
                if not header[0].startswith("#"):
                    header[0] = "#" + header[0]
                print >>out, "\t".join(header + extra_header)
            if header == toks: continue

        if not isinstance(toks, ABase):
            f = Feature()
            f.chrom = toks[0]
            f.txStart = int(toks[1])
            f.txEnd = int(toks[2])
            try:
                f.strand = toks[header.index('strand')]
            except ValueError:
                pass
        else:
            f = toks
            # for now, use the objects str to get the columns
            # might want to use getattr on the original cols

            toks = f.bed(*header).split("\t")
        sep = "^*^"
        for ti, tbl in enumerate(tables):
            if in_memory:
                objs = intersecters[ti].knearest(int(toks[1]), int(toks[2]), chrom=toks[0], k = 1)
            else:
                objs = g.knearest(tbl, toks[0], int(toks[1]), int(toks[2]), k=1)
            if len(objs) == 0:
                print >>out, "\t".join(toks + ["", "", ""])
                continue

            gp = hasattr(objs[0], "exonStarts")
            names = [o.gene_name for o in objs]
            if feature_strand:
                strands = [-1 if f.is_upstream_of(o) else 1 for o in objs]
            else:
                strands = [-1 if o.is_upstream_of(f) else 1 for o in objs]

            # dists can be a list of tuples where the 2nd item is something
            # like 'island' or 'shore'
            dists = [o.distance(f, features=gp) for o in objs]
            pure_dists = [d[0] if isinstance(d, (tuple, list)) else d for d in dists]

            # convert to negative if the feature is upstream of the query
            for i, s in enumerate(strands):
                if s == 1: continue
                if isinstance(pure_dists[i], basestring): continue
                pure_dists[i] *= -1

            for i, (pd, d) in enumerate(zip(pure_dists, dists)):
                if isinstance(d, tuple):
                    if len(d) > 1:
                        dists[i] = "%s%s%s" % (pd, sep, sep.join(d[1:]))
                    else:
                        dists[i] = pd
            # keep uniqe name, dist combinations (occurs because of
            # transcripts)
            name_dists = set(["%s%s%s" % (n, sep, d) \
                            for (n, d) in zip(names, dists)])
            name_dists = [nd.split(sep) for nd in name_dists]

            for i in range(len(name_dists[0])): # iterate over the dist, feature, name cols

                toks.append(";".join(nd[i] for nd in name_dists))
        print >>out, "\t".join(toks)

    if close:
        out.close()
    return out.name

########NEW FILE########
__FILENAME__ = blat_blast
import requests
from .models import Blat

def blat(seq, name, db, seq_type="DNA"):
    r = requests.post('http://genome.ucsc.edu/cgi-bin/hgBlat',
            data=dict(db=db, type=seq_type, userSeq=seq, output="html"))
    if "Sorry, no matches found" in r.text:
        raise StopIteration
    text = r.text.split("<TT><PRE>")[1].split("</PRE></TT>")[0].strip().split("\n")
    for istart, line in enumerate(text):
        if "-----------" in line: break
    istart += 1
    for i, hit in enumerate(t.rstrip("\r\n") for t in text[istart:]):
        hit = hit.split(" YourSeq ")[1].split()
        f = Blat()
        # blat returns results without chr prefix
        if not hit[5].startswith("chr"): hit[5] = "chr" + hit[5]
        f.chrom = hit[5]
        f.txStart = long(hit[7]) - 1 # blat returns 1-based hits.
        f.txEnd = long(hit[8])
        f.strand = hit[6]
        f.identity = float(hit[4].rstrip("%"))
        f.span = int(hit[-1])
        f.db = db
        f.name = "blat-hit-%i-to-%s (%i bp)" % (i + 1, name, f.span)
        yield f

def blat_all(seq, name, dbs, seq_type="DNA"):
    for db in dbs:
        for f in blat(seq, name, db, seq_type):
            yield f



########NEW FILE########
__FILENAME__ = intersecter
import operator
import collections

class Feature(object):
    """\
    Basic feature, with required integer start and end properties.
    Also accpets optional strand as +1 or -1 (used for up/downstream queries),
    a name

    >>> from intersecter import Feature

    >>> f1 = Feature(23, 36)
    >>> f2 = Feature(34, 48, strand=-1)
    >>> f2
    Feature(34, 48, strand=-1)

    """
    __slots__ = ("start", "end", "strand", "chrom")

    def __init__(self, start, end, strand=0, chrom=None):
        assert start <= end, "start must be less than end"
        self.start  = start
        self.end   = end
        self.strand = strand
        self.chrom  = chrom

    def __repr__(self):
        fstr = "Feature(%d, %d" % (self.start, self.end)
        if self.chrom is not None:
            fstr += ", chrom=%s" % self.chrom
        if self.strand != 0:
            fstr += ", strand=%d" % self.strand
        fstr += ")"
        return fstr

def binsearch_left_start(intervals, x, lo, hi):
    while lo < hi:
        mid = (lo + hi)//2
        f = intervals[mid]
        if f.start < x: lo = mid + 1
        else: hi = mid
    return lo

# like python's bisect_right find the _highest_ index where the value x 
# could be inserted to maintain order in the list intervals
def binsearch_right_end(intervals, x, lo, hi):
    while lo < hi:
        mid = (lo + hi)/2
        f = intervals[mid]
        if x < f.start: hi = mid
        else: lo = mid + 1
    return lo

class Intersecter(object):
    """\
    Data structure for performing intersect and neighbor queries on a
    set of intervals. Algorithm uses simple binary search along with
    knowledge of the longest interval to perform efficient queries.

    Usage
    =====
    >>> from intersecter import Intersecter, Feature

    Add intervals, the only requirement is that the interval have integer
    start and end attributes. Optional arguments are strand, and chrom.

    >>> f = Feature(1, 22, strand=-1)
    >>> f
    Feature(1, 22, strand=-1)

    >>> features = [
    ...            Feature(0, 10, -1),
    ...            Feature(3, 7, 1),
    ...            Feature(3, 40, -1),
    ...            Feature(13, 50, 1)
    ... ]

    >>> intersecter = Intersecter(features)

    Queries
    -------

    find
    ++++

    >>> intersecter.find(2, 5)
    [Feature(0, 10, strand=-1), Feature(3, 7, strand=1), Feature(3, 40, strand=-1)]
    >>> intersecter.find(11, 100)
    [Feature(3, 40, strand=-1), Feature(13, 50, strand=1)]
    >>> intersecter.find(100, 200)
    []

    left/right
    ++++++++++
    the left method finds features that are strictly to the left of
    the query feature. overlapping features are not considered:

    >>> intersecter.left(Feature(0, 1))
    []
    >>> intersecter.left(Feature(11, 12))
    [Feature(0, 10, strand=-1)]


    up/downstream
    +++++++++++++
    up/downstream method behave exactly like left/right, except that
    the direction is determined by the strand of the query feature. 
    If the strand is 1, then upstream is left, downstream is right.

    If the strand is -1, then upstream is right, downstream is left.
    >>> intersecter.upstream(Feature(11, 12, strand=1))
    [Feature(0, 10, strand=-1)]
    >>> intersecter.upstream(Feature(11, 12, strand=-1))
    [Feature(13, 50, strand=1)]

    all of these method take an argument 'n' for the number of results desired.
    >>> intersecter.upstream(Feature(1, 2, strand=-1), n=3)
    [Feature(3, 7, strand=1), Feature(3, 40, strand=-1), Feature(13, 50, strand=1)]

    nearest neighbors
    +++++++++++++++++
    >>> intersecter.knearest(Feature(1, 2))
    [Feature(0, 10, strand=-1)]

    >>> intersecter.knearest(Feature(1, 2), k=2)
    [Feature(0, 10, strand=-1), Feature(3, 40, strand=-1), Feature(3, 7, strand=1)]

    """

    # since intervals are sorted by start, also have to know the max_len (see find)
    # cdef int max_len
    # if an item is added, the list must be resorted.

    # ---- Basic API --------------------------------------------------

    def __init__(self, intervals):
        self.intervals = collections.defaultdict(list)
        self.max_len = {}

        for i, iv in enumerate(intervals):
            self.intervals[iv.chrom].append(iv)
        for chrom in self.intervals:
            self.intervals[chrom].sort(key=operator.attrgetter('start'))
            self.max_len[chrom] = max(1, max([i.end - i.start for i in self.intervals[chrom]]))


    def find(self, start, end, chrom=None):
        """Return a object of all stored intervals intersecting between (start, end) inclusive."""
        intervals = self.intervals[chrom]
        ilen = len(intervals)
        # NOTE: we only search for starts, since any feature that starts within max_len of
        # the query could overlap, we must subtract max_len from the start to get the needed
        # search space. everything else proceeds like a binary search.
        # (but add distance calc for candidates).
        if not chrom in self.max_len: return []
        ileft  = binsearch_left_start(intervals, start - self.max_len[chrom], 0, ilen)
        iright = binsearch_right_end(intervals, end, ileft, ilen)
        query = Feature(start, end)
        # we have to check the distance to make sure we didnt pick up anything 
        # that started within max_len, but wasnt as long as max_len
        return [f for f in intervals[ileft:iright] if distance(f, query) == 0]

    def left(self, f, n=1):
        """return the nearest n features strictly to the left of a Feature f.
        Overlapping features are not considered as to the left.

        f: a Feature object
        n: the number of features to return
        """
        intervals = self.intervals[f.chrom]
        if intervals == []: return []

        iright = binsearch_left_start(intervals, f.start, 0 , len(intervals)) + 1
        ileft  = binsearch_left_start(intervals, f.start - self.max_len[f.chrom] - 1, 0, 0)

        results = sorted((distance(other, f), other) for other in intervals[ileft:iright] if other.end < f.start and distance(f, other) != 0)
        if len(results) == n:
            return [r[1] for r in results]

        # have to do some extra work here since intervals are sorted
        # by starts, and we dont know which end may be around...
        # in this case, we got some extras, just return as many as
        # needed once we see a gap in distances.
        for i in range(n, len(results)):
            if results[i - 1][0] != results[i][0]:
                return [r[1] for r in results[:i]]

        if ileft == 0:
            return [r[1] for r in results]

        # here, didn't get enough, so move left and try again. 
        1/0

    def right(self, f, n=1):
        """return the nearest n features strictly to the right of a Feature f.
        Overlapping features are not considered as to the right.

        f: a Feature object
        n: the number of features to return
        """
        intervals = self.intervals[f.chrom]
        ilen = len(intervals)
        iright = binsearch_right_end(intervals, f.end, 0, ilen)
        results = []

        while iright < ilen:
            i = len(results)
            if i > n:
                if distance(f, results[i - 1]) != distance(f, results[i - 2]):
                    return results[:i - 1]
            other = intervals[iright]
            iright += 1
            if distance(other, f) == 0: continue
            results.append(other)
        return results


    def upstream(self, f, n=1):
        """find n upstream features where upstream is determined by
        the strand of the query Feature f
        Overlapping features are not considered.

        f: a Feature object
        n: the number of features to return
        """
        if f.strand == -1:
            return self.right(f, n)
        return self.left(f, n)


    def downstream(self, f, n=1):
        """find n downstream features where downstream is determined by
        the strand of the query Feature f
        Overlapping features are not considered.

        f: a Feature object
        n: the number of features to return
        """
        if f.strand == -1:
            return self.left(f, n)
        return self.right(f, n)

    def knearest(self, f_or_start, end=None, chrom=None, k=1):
        """return the n nearest neighbors to the given feature
        f: a Feature object
        k: the number of features to return
        """


        if end is not None:
            f = Feature(f_or_start, end, chrom=chrom)
        else:
            f = f_or_start

        DIST = 2000
        feats = filter_feats(self.find(f.start - DIST, f.end + DIST, chrom=f.chrom), f, k)
        if len(feats) >= k:
            return feats

        nfeats = k - len(feats)
        fleft = Feature(f.start - DIST, f.start, chrom=f.chrom)
        feats.extend(self.left(fleft, n=nfeats))

        fright = Feature(f.end, f.end + DIST, chrom=f.chrom)
        feats.extend(self.right(fright, n=nfeats))
        return filter_feats(feats, f, k)


def distance(f1, f2):
    """\
    Distance between 2 features. The integer result is always positive or zero.
    If the features overlap or touch, it is zero.
    >>> from intersecter import Feature, distance
    >>> distance(Feature(1, 2), Feature(12, 13))
    10
    >>> distance(Feature(1, 2), Feature(2, 3))
    0
    >>> distance(Feature(1, 100), Feature(20, 30))
    0

    """
    if f1.end < f2.start: return f2.start - f1.end
    if f2.end < f1.start: return f1.start - f2.end
    return 0

def filter_feats(intervals, f, k):
    feats = sorted((distance(f, iv), iv) for iv in intervals if iv is not None)
    kk = k
    while kk < len(feats) and feats[k - 1][0] == feats[kk][0]:
        kk += 1
    return [f[1] for f in feats[:kk]]

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = mirror
# from http://www.tylerlesmann.com/2009/apr/27/copying-databases-across-platforms-sqlalchemy/

from sqlalchemy import create_engine, Table, select, Enum, Column, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.mysql import LONGBLOB, ENUM
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.types import VARCHAR
import sqlalchemy
import sys
import os


def make_session(connection_string):
    if "///" in connection_string and \
        os.path.exists(connection_string.split("///")[1]) and \
        connection_string.startswith("sqlite"):
            print >>sys.stderr, "attempting to add to existing sqlite database"
    engine = create_engine(connection_string, echo=False, convert_unicode=True)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False,
            autocommit=False)
    engine.connect()
    return Session(), engine

def page_query(q, session, limit=8000):
    #if q.count() < 80000:
    #    for rn q.all()
    offset = 0
    while True:
        elem = None
        for elem in session.execute(q.offset(offset).limit(limit)):
            yield elem
        offset += limit
        if elem is None:
            break

def set_table(genome, table, table_name, connection_string, metadata):
    """
    alter the table to work between different
    dialects
    """
    table = Table(table_name, genome._metadata, autoload=True,
                    autoload_with=genome.bind, extend_existing=True)

    #print "\t".join([c.name for c in table.columns])
    # need to prefix the indexes with the table name to avoid collisions
    for i, idx in enumerate(table.indexes):
        idx.name = table_name + "." + idx.name + "_ix" + str(i)

    cols = []
    for i, col in enumerate(table.columns):
        # convert mysql-specific types to varchar
        #print col.name, col.type, isinstance(col.type, ENUM)
        if isinstance(col.type, (LONGBLOB, ENUM)):

            if 'sqlite' in connection_string:
                col.type = VARCHAR()
            elif 'postgres' in connection_string:
                if isinstance(col.type, ENUM):
                    #print dir(col)
                    col.type = PG_ENUM(*col.type.enums, name=col.name,
                        create_type=True)
                else:
                    col.type = VARCHAR()
        elif str(col.type) == "VARCHAR" \
                and ("mysql" in connection_string \
                or "postgres" in connection_string):
            if col.type.length is None:
                col.type.length = 48 if col.name != "description" else None
        if not "mysql" in connection_string:
            if str(col.type).lower().startswith("set("):
                col.type = VARCHAR(15)
        cols.append(col)

    table = Table(table_name, genome._metadata, *cols,
            autoload_replace=True, extend_existing=True)

    return table

def mirror(genome, tables, connection_string):
    destination, dengine = make_session(connection_string)
    dmeta = MetaData(bind=dengine)

    orig_counts = []
    for table_name in tables:
        # cause it ot be mapped
        table = getattr(genome, table_name)._table
        print >>sys.stderr, 'Mirroring', table_name

        table = set_table(genome, table, table_name,
                connection_string, dmeta)
        try:
            table.create(dengine)
        except sqlalchemy.exc.OperationalError:
            pass

        destination.commit()
        ins = table.insert()

        columns = table.columns.keys()
        records = []
        table_obj = getattr(genome, table_name)._table
        t = getattr(genome, table_name)
        for ii, record in enumerate(page_query(table_obj.select(), t.session)):
            data = dict(
                (str(column), getattr(record, column)) for column in columns
            )
            records.append(data)
            if ii % 20000 == 0 and ii > 0:
                destination.execute(ins, records)
                print >>sys.stderr, "processing record %i" % ii
                destination.commit()
                records = []
        destination.execute(ins, records)
        destination.commit()
        orig_counts.append(getattr(genome, table_name).count())

    destination, dengine = make_session(connection_string)
    from . import Genome
    newg = Genome(connection_string)
    new_counts = [getattr(newg, table_name).count() for table_name in tables]
    for tbl, oc, nc in zip(tables, orig_counts, new_counts):
        if oc != nc: print >>sys.stderr, "ERROR: mirrored table '%s' has %i \
            rows while the original had %i" % (tbl, nc, oc)
    return newg

if __name__ == "__main__":
    if True:
        from cruzdb import Genome
        g = Genome('hg18')

        mirror(g, ['chromInfo'], 'sqlite:////tmp/u.db')

########NEW FILE########
__FILENAME__ = models
"""
This is used to create a Model with the appropriate methods
from a UCSC table. It uses sqlalchemy reflection to
do the lifiting.

"""
from sqlalchemy import Column, String, ForeignKey, Float, Integer
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import PrimaryKeyConstraint

import sys
from operator import itemgetter

# needed to avoid circular imports
#CHANGED:from init import Base
from sequence import sequence as _sequence
from __init__ import Genome


import re

def _ncbi_parse(html):
    from collections import OrderedDict

    try:
        info = html.split("Sequences producing significant alignments")[1].split("<tbody>")[1]
    except IndexError:
        print >>sys.stderr, html
        raise
    info = info.split("</table>")[0]
    regexp = re.compile(r'<tr>(.+?)(<\/tr>)', re.MULTILINE | re.DOTALL)
    tdreg = re.compile(r'<td.*?>(.+?)(?:</td>)', re.MULTILINE | re.DOTALL)
    colnames = ("accession", "org", "description", "max_score", "total_score",
                    "query_coverage", "e_value", "max_ident", "link")
    for record in (r.groups(0)[0] for r in regexp.finditer(info)):
        try:
            cols = tdreg.findall(record)
            pcols = [c.split(">")[1].split("<")[0].strip() if "<" in c else c.strip() for c in cols[:-1]]
            pcols.insert(1, " ".join(pcols[1].replace("PREDICTED: ", "").split(" ")[:2]))
            try:
                pcols.append(cols[-1].split("href=")[1].split(">")[0])
            except IndexError: # no link
                pcols.append("")
            yield OrderedDict(zip(colnames, pcols))
        except:
            print >>sys.stderr, record

class CruzException(Exception):
    pass

class Interval(object):
    """
    Interval class for convenience

    Parameters
    ----------

    start : int
    
    end : int

    chrom : str

    name : str
        optional name for the interval
    """

    __slots__ = ('chrom', 'start', 'end', 'name', 'gene_name')
    def __init__(self, start, end, chrom=None, name=None):
        self.start, self.end = start, end
        self.chrom = chrom
        self.name = self.gene_name = name

    def overlaps(self, other):
        """
        check for overlap with the other interval
        """
        if self.chrom != other.chrom: return False
        if self.start > other.end: return False
        if other.start > self.end: return False
        return True

    def is_upstream_of(self, other):
        """
        check if this is upstream of the `other` interval taking the strand of
        the other interval into account
        """
        if self.chrom != other.chrom: return None
        if getattr(other, "strand", None) == "+":
            return self.end <= other.start
        # other feature is on - strand, so this must have higher start
        return self.start >= other.end

    def distance(self, other_or_start=None, end=None, features=False):
        """
        check the distance between this an another interval
        Parameters
        ----------

        other_or_start : Interval or int
            either an integer or an Interval with a start attribute indicating
            the start of the interval

        end : int
            if `other_or_start` is an integer, this must be an integer
            indicating the end of the interval

        features : bool
            if True, the features, such as CDS, intron, etc. that this feature
            overlaps are returned.
        """
        if end is None:
            assert other_or_start.chrom == self.chrom

        other_start, other_end = get_start_end(other_or_start, end)

        if other_start > self.end:
            return other_start - self.end
        if self.start > other_end:
            return self.start - other_end
        return 0

class ABase(object):
    """
    Base object that wraps returned database rows
    """

    _prefix_chain = ("tx", "chrom")
    @declared_attr
    def __tablename__(cls):
        return cls.__name__
    __table_args__ = {'autoload': True}
    __mapper_args__= {'always_refresh': False, 'exclude_properties': ['dist', '_dist']}

    anno_cols = ("name", "distance", "feature")

    @property
    def is_coding(self):
        try:
            return self.cdsStart != self.cdsEnd
        except AttributeError:
            return False

    def _repr_html_(self):
        info = dict(db=self.db, start=self.start, end=self.end,
                chrom=self.chrom)

        info['name'] = self.__class__.name
        url = "http://genome.ucsc.edu/cgi-bin/hgTracks?position=%(chrom)s:%(start)s-%(end)s&db=%(db)s&%(name)s=full"  % info
        return "<iframe src='%s' style='margin:0px; border:0; height:500px; width:100%%' ></iframe>" % url

    @property
    def exons(self):
        """
        return a list of exons [(start, stop)] for this object if appropriate
        """
        # drop the trailing comma
        if not self.is_gene_pred: return []
        if hasattr(self, "exonStarts"):
            starts = (long(s) for s in self.exonStarts[:-1].split(","))
            ends = (long(s) for s in self.exonEnds[:-1].split(","))
        else: # it is bed12
            starts = [self.start + long(s) for s in self.chromStarts[:-1].split(",")]
            ends = [starts[i] + long(size) for i, size \
                    in enumerate(self.blockSizes[:-1].split(","))]


        return zip(starts, ends)

    @property
    def gene_features(self):
        """
        return a list of features for the gene features of this object.
        This would include exons, introns, utrs, etc.
        """
        nm, strand = self.gene_name, self.strand
        feats = [(self.chrom, self.start, self.end, nm, strand, 'gene')]
        for feat in ('introns', 'exons', 'utr5', 'utr3', 'cdss'):
            fname = feat[:-1] if feat[-1] == 's' else feat
            res = getattr(self, feat)
            if res is None or all(r is None for r in res): continue
            if not isinstance(res, list): res = [res]
            feats.extend((self.chrom, s, e, nm, strand, fname) for s, e in res)

        tss = self.tss(down=1)
        if tss is not None:
            feats.append((self.chrom, tss[0], tss[1], nm, strand, 'tss'))
            prom = self.promoter()
            feats.append((self.chrom, prom[0], prom[1], nm, strand, 'promoter'))

        return sorted(feats, key=itemgetter(1))

    def tss(self, up=0, down=0):
        """
        Return a start, end tuple of positions around the transcription-start
        site

        Parameters
        ----------

        up : int
           if greature than 0, the strand is used to add this many upstream
           bases in the appropriate direction

        down : int
           if greature than 0, the strand is used to add this many downstream
           bases into the gene.
        """
        if not self.is_gene_pred: return None
        tss = self.txEnd if self.strand == '-' else self.txStart
        start, end = tss, tss
        if self.strand == '+':
            start -= up
            end += down
        else:
            start += up
            end -= down
            start, end = end, start
        return max(0, start), max(end, start, 0)

    def promoter(self, up=2000, down=0):
        """
        Return a start, end tuple of positions for the promoter region of this
        gene

        Parameters
        ----------

        up : int
           this distance upstream that is considered the promoter

        down : int
           the strand is used to add this many downstream bases into the gene.
        """
        if not self.is_gene_pred: return None
        return self.tss(up=up, down=down)

    @property
    def coding_exons(self):
        """
        includes the entire exon as long as any of it is > cdsStart and <
        cdsEnd
        """
        # drop the trailing comma
        starts = (long(s) for s in self.exonStarts[:-1].split(","))
        ends = (long(s) for s in self.exonEnds[:-1].split(","))
        return [(s, e) for s, e in zip(starts, ends)
                                          if e > self.cdsStart and
                                             s < self.cdsEnd]

    @property
    def cds(self):
        """just the parts of the exons that are translated"""
        ces = self.coding_exons
        if len(ces) < 1: return ces
        ces[0] = (self.cdsStart, ces[0][1])
        ces[-1] = (ces[-1][0], self.cdsEnd)
        assert all((s < e for s, e in ces))
        return ces

    cdss = cds

    def _cds_sequence(self, cds):
        seqs = []
        if len(cds) == 0: return []
        # grab all the sequences at once to reduce number of requests.
        all_seq = _sequence(self.db, self.chrom, cds[0][0] + 1, cds[-1][1])
        if len(cds) == 1:
            return all_seq
        lowest = cds[0][0]
        cds0 = [(s - lowest, e - lowest) for s, e in cds]
        for cstart, cend in cds0:
            seqs.append(all_seq[cstart:cend])
        return seqs

    @property
    def cds_sequence(self):
        """
        a list of genomic sequences for the CDS's
        """
        return self._cds_sequence(self.cds)

    @property
    def mrna_sequence(self):
        """
        a list of genomic sequences for the mRNA's
        """
        return self._cds_sequence(self.coding_exons)

    @property
    def browser_link(self):
        return "http://genome.ucsc.edu/cgi-bin/hgTracks?db=%s&position=%s" % (self.db, self.position)

    @property
    def position(self):
        " a chrom:start-stop representation of this feature"
        return "%s:%i-%i" % (self.chrom, self.start, self.end)

    @property
    def bins(self):
        """
        return the bins for efficient querying
        """
        return Genome.bins(self.start, self.end)

    def _introns(self, exons=None):
        if not self.is_gene_pred: return []
        se = self.exons
        if not (se or exons) or exons == []: return []
        starts, ends = zip(*exons) if exons is not None else zip(*se)
        return [(e, s) for e, s in zip(ends[:-1], starts[1:])]

    introns = property(_introns)

    def _xstream(self, s, e):
        f = Feature()
        f.txStart = s
        f.txEnd = e
        f.name = "region"
        f.cdsStart = f.cdsEnd = s
        f.strand = self.strand
        f.chrom = self.chrom
        return f

    def is_upstream_of(self, other):
        """
        return a boolean indicating whether this feature is upstream of `other`
        taking the strand of other into account
        """
        if self.chrom != other.chrom: return None
        if getattr(other, "strand", None) == "-":
            # other feature is on - strand, so this must have higher start
            return self.start >= other.end
        return self.end <= other.start

    def is_downstream_of(self, other):
        """
        return a boolean indicating whether this feature is downstream of
        `other` taking the strand of other into account
        """
        if self.chrom != other.chrom: return None
        if getattr(other, "strand", None) == "-":
            # other feature is on - strand, so this must have higher start
            return self.end <= other.start
        return self.start >= other.end

    def features(self, other_start, other_end):
        """
        return e.g. "intron;exon" if the other_start, end overlap introns and
        exons
        """
        # completely encases gene.
        if other_start <= self.start and other_end >= self.end:
            return ['gene' if self.cdsStart != self.cdsEnd else 'nc_gene']
        other = Interval(other_start, other_end)
        ovls = []
        tx = 'txEnd' if self.strand == "-" else 'txStart'
        if hasattr(self, tx) and other_start <= getattr(self, tx) <= other_end \
            and self.cdsStart != self.cdsEnd:
                ovls = ["TSS"]
        for ftype in ('introns', 'exons', 'utr5', 'utr3', 'cdss'):
            feats = getattr(self, ftype)
            if not isinstance(feats, list): feats = [feats]
            if any(Interval(f[0], f[1]).overlaps(other) for f in feats):
                ovls.append(ftype[:-1] if ftype[-1] == 's' else ftype)
        if 'cds' in ovls:
            ovls = [ft for ft in ovls if ft != 'exon']
        if self.cdsStart == self.cdsEnd:
            ovls = ['nc_' + ft for ft in ovls]
        return ovls

    def distance(self, other_or_start=None, end=None, features=False):
        """
        check the distance between this an another interval
        Parameters
        ----------

        other_or_start : Interval or int
            either an integer or an Interval with a start attribute indicating
            the start of the interval

        end : int
            if `other_or_start` is an integer, this must be an integer
            indicating the end of the interval

        features : bool
            if True, the features, such as CDS, intron, etc. that this feature
            overlaps are returned.
        """
        if end is None:
            assert other_or_start.chrom == self.chrom

        other_start, other_end = get_start_end(other_or_start, end)

        if other_start > self.end:
            return other_start - self.end, "intergenic"
        if self.start > other_end:
            return self.start - other_end, "intergenic"
        if features: return (0, "+".join(self.features(other_start, other_end)))
        return (0, "")

    def upstream(self, distance):
        """
        return the (start, end) of the region before the geneStart
        """
        if getattr(self, "strand", None) == "+":
            e = self.start
            s = e - distance
        else:
            s = self.end
            e = s + distance
        return self._xstream(s, e)

    def downstream(self, distance):
        """
        return the (start, end) of the region before the geneStart
        """
        if getattr(self, "strand", None) == "+":
            s = self.end
            e = s + distance
        else:
            e = self.start
            s = e - distance
        return self._xstream(s, e)

    @property
    def utr5(self):
        """
        return the 5' UTR if appropriate
        """
        if not self.is_coding or len(self.exons) < 2: return (None, None)
        if self.strand == "+":
            s, e = (self.txStart, self.cdsStart)
        else:
            s, e = (self.cdsEnd, self.txEnd)
        if s == e: return (None, None)
        return s, e

    @property
    def utr3(self):
        """
        return the 3' UTR if appropriate
        """
        if not self.is_coding or len(self.exons) < 2: return (None, None)
        if self.strand == "-":
            s, e = (self.txStart, self.cdsStart)
        else:
            s, e = (self.cdsEnd, self.txEnd)
        if s == e: return (None, None)
        return s, e

    def __len__(self):
        return self.end - self.start

    def __cmp__(self, other):
        if self.chrom != getattr(other, "chrom", other): return 0
        if self.start < other.start: return -1
        return 1

    @property
    def start(self):
        for prefix in self._prefix_chain:
            try: return getattr(self, prefix + "Start")
            except AttributeError: pass
        raise Exception("no start for %r" % self)

    @property
    def end(self):
        for prefix in self._prefix_chain:
            try: return getattr(self, prefix + "End")
            except AttributeError: pass
        raise Exception("no end for %r" % self)


    def __repr__(self):
        try:
            self.start
            return "%s(%s:%s:%i-%i)" % (self.__class__.__name__, self.chrom, self.gene_name,
                self.start, self.end)
        except:
            try:
                return "%s(%s)" % (self.__tablename__, self.chrom)
            except:
                attr = [x.name for x in self._table.columns if "name" in
                        x.name.lower()][-1]
                name = getattr(self, attr)
                return "%s(\"%s\")" % (self.__tablename__, name)


    @property
    def gene_name(self):
        if hasattr(self, "name2"): return self.name2
        if hasattr(self, "name"): return self.name
        return self.position

    @property
    def db(self):
        # grab the database name from the current row
        # e.g. hg18
        return self._table.bind.url.database

    def __str__(self):
        # output something bed-like
        fields = "chrom start end gene_name".split()
        s = "\t".join(map(str, (getattr(self, field) for field in fields)))
        if hasattr(self, "score"):
            s += "\t%.2f" % (self.score)
            if hasattr(self, "strand"):
                s += "\t%s" % (self.strand)

        elif hasattr(self, "strand"):
            s += "\t.\t%s" % (self.strand)
        return s

    def sequence(self, per_exon=False):
        """
        Return the sequence for this feature.
        if per-exon is True, return an array of exon sequences
        This sequence is never reverse complemented
        """
        db = self.db
        if not per_exon:
            start = self.txStart + 1
            return _sequence(db, self.chrom, start, self.txEnd)
        else:
            # TODO: use same strategy as cds_sequence to reduce # of requests.
            seqs = []
            for start, end in self.exons:
                seqs.append(_sequence(db, self.chrom, start + 1, end))
            return seqs

    def __iter__(self):
        for k in self._table.columns:
            yield str(getattr(self, k.name, ""))

    def ncbi_blast(self, db="nr", megablast=True, sequence=None):
        """
        perform an NCBI blast against the sequence of this feature
        """
        import requests
        requests.defaults.max_retries = 4
        assert sequence in (None, "cds", "mrna")
        seq = self.sequence() if sequence is None else ("".join(self.cds_sequence if sequence == "cds" else self.mrna_sequence))
        r = requests.post('http://blast.ncbi.nlm.nih.gov/Blast.cgi',
                        timeout=20,
                        data=dict(
                            PROGRAM="blastn",
                            #EXPECT=2,
                            DESCRIPTIONS=100,
                            ALIGNMENTS=0,
                            FILTER="L", # low complexity
                            CMD="Put",
                            MEGABLAST=True,
                            DATABASE=db,
                            QUERY=">%s\n%s" % (self.name, seq)
                        )
                    )

        if not ("RID =" in r.text and "RTOE" in r.text):
            print >>sys.stderr, "no results"
            raise StopIteration
        rid = r.text.split("RID = ")[1].split("\n")[0]

        import time
        time.sleep(4)
        print >>sys.stderr, "checking..."
        r = requests.post('http://blast.ncbi.nlm.nih.gov/Blast.cgi',
                data=dict(RID=rid, format="Text",
                    DESCRIPTIONS=100,
                    DATABASE=db,
                    CMD="Get", ))
        while "Status=WAITING" in r.text:
            print >>sys.stderr, "checking..."
            time.sleep(10)
            r = requests.post('http://blast.ncbi.nlm.nih.gov/Blast.cgi',
                data=dict(RID=rid, format="Text",
                    CMD="Get", ))
        for rec in _ncbi_parse(r.text):
            yield rec

    def blat(self, db=None, sequence=None, seq_type="DNA"):
        """
        make a request to the genome-browsers BLAT interface
        sequence is one of None, "mrna", "cds"
        returns a list of features that are hits to this sequence.
        """
        from . blat_blast import blat, blat_all
        assert sequence in (None, "cds", "mrna")
        seq = self.sequence() if sequence is None else ("".join(self.cds_sequence if sequence == "cds" else self.mrna_sequence))
        if isinstance(db, (tuple, list)):
            return blat_all(seq, self.gene_name, db, seq_type)
        else:
            return blat(seq, self.gene_name, db or self.db, seq_type)

    @property
    def is_gene_pred(self):
        """
        http://genome.ucsc.edu/FAQ/FAQformat.html#format9
        """
        return hasattr(self, "exonStarts") or hasattr(self, 'chromStarts')

    def bed(self, *attrs, **kwargs):
        """
        return a bed formatted string of this feature
        """
        exclude = ("chrom", "start", "end", "txStart", "txEnd", "chromStart",
                "chromEnd")
        if self.is_gene_pred:
            return self.bed12(**kwargs)
        return "\t".join(map(str, (
                 [self.chrom, self.start, self.end] +
                 [getattr(self, attr) for attr in attrs if not attr in exclude]
                         )))


    def bed12(self, score="0", rgb="."):
        """
        return a bed12 (http://genome.ucsc.edu/FAQ/FAQformat.html#format1)
        representation of this interval
        """
        if not self.is_gene_pred:
            raise CruzException("can't create bed12 from non genepred feature")
        exons = self.exons
        # go from global start, stop, to relative start, length...
        sizes = ",".join([str(e[1] - e[0]) for e in exons]) + ","
        starts = ",".join([str(e[0] - self.txStart) for e in exons]) + ","
        name = self.name2 + "," + self.name if hasattr(self, "name2") \
                                            else self.name
        return "\t".join(map(str, (
            self.chrom, self.txStart, self.txEnd, name,
            score, self.strand, self.cdsStart, self.cdsEnd, rgb,
            len(exons), sizes, starts)))

    def globalize(self, position, cdna=True):
        1/0
        start, end = (self.cdsStart, self.cdsEnd) if cdna else \
                                        (self.start, self.end)
        exons = self.exons or None
        pos = position + start
        if exons is None:
            return pos

        subtract = 0
        print >>sys.stderr, "exon lengths:", sum((ie - ib) for ib, ie in self.exons)
        for estart, eend in exons:
            if iend < pos:
                subtract += (iend - istart)
            elif istart < pos and iend > pos:
                subtract += (pos - istart)
            print >>sys.stderr, subtract, (istart, iend), pos
        return pos - subtract

    def localize(self, *positions, **kwargs):
        """
        convert global coordinate(s) to local taking
        introns into account and cds/tx-Start depending on cdna=True kwarg
        """
        cdna = kwargs.get('cdna', False)
        # TODO: account for strand ?? add kwarg ??
        # if it's to the CDNA, then it's based on the cdsStart
        start, end = (self.cdsStart, self.cdsEnd) if cdna else \
                                        (self.start, self.end)
        introns = self.introns or None
        if cdna:
            if not self.is_coding:
                return ([None] * len(positions)) if len(positions) > 1 else None
            introns = self._introns(self.cds) or None

        if introns is None:
            local_ps = [p - start if (start <= p < end) else None for p in positions]
            return local_ps[0] if len(positions) == 1 else local_ps

        introns = [(s - start, e - start) for s, e in introns]
        positions = [p - start for p in positions]
        # now both introns and positions are local starts based on cds/tx-Start
        local_ps = []
        l = end - start
        for original_p in positions:
            subtract = 0
            p = original_p
            print >>sys.stderr, p, l
            if p < 0 or p >= l: # outside of transcript
                local_ps.append(None)
                continue
            for s, e in introns:
                # within intron
                if s <= p <= e:
                    subtract = None
                    break
                # otherwise, adjust for intron length.
                elif p >= e:
                    subtract += (e - s)

            local_ps.append(p - subtract if subtract is not None else None)

        assert all(p >=0 or p is None for p in local_ps), (local_ps)
        return local_ps[0] if len(positions) == 1 else local_ps


def get_start_end(other_or_start, end):
    if end is None:
        other_start, other_end = other_or_start.start, other_or_start.end
    else:
        other_start, other_end = other_or_start, end
    return other_start, other_end

class Feature(ABase):
    name = Column(String, unique=False, primary_key=True)

class cpgIslandExt(Feature):
    anno_cols = ("name", "distance", "feature")

    def distance(self, other_or_start=None, end=None, features="unused",
            shore_dist=3000):
        """
        check the distance between this an another interval
        Parameters
        ----------

        other_or_start : Interval or int
            either an integer or an Interval with a start attribute indicating
            the start of the interval

        end : int
            if `other_or_start` is an integer, this must be an integer
            indicating the end of the interval

        features : bool
            if True, the features, such as CDS, intron, etc. that this feature
            overlaps are returned.
        """
        # leave features kwarg to match signature from Feature.distance
        if end is None:
            assert other_or_start.chrom == self.chrom
        other_start, other_end = get_start_end(other_or_start, end)

        dist = 0
        if other_start > self.end:
            dist = other_start - self.end
        elif self.start > other_end:
            dist = self.start - other_end
        assert dist >= 0

        if dist > 0: dist = (dist, "shore" if abs(dist) <= shore_dist else "")
        else: dist = (0, "island")
        return dist

cpgRafaLab = cpgIslandExt

class SNP(ABase):
    __table_args__ = (
            PrimaryKeyConstraint('name', 'chrom', 'chromStart'),
            dict(autoload=True),)
    # can't add name or it gives error on select.
    #name = Column(String, unique=False)
    @property
    def name2(self):
        return self.name + (("-" + self.func) if self.func != "unknown" else "")

    def to_simple(self):
        return Interval(self.chromStart, self.chromEnd, self.chrom, self.name2)

class chromInfo(ABase):
    def __repr__(self):
        return "%s(%s:%i)" % (self.__tablename__, self.chrom, self.size)

    __str__ = __repr__



class Blat(Feature):

    identity = Column(Float)
    span = Column(Integer)
    db = Column(String(6))

    def __str__(self):
        res = Feature.__str__(self).replace("\t.\t", "\t%.1f%%\t" % self.identity)
        res += "\t%s\t%s" % (self.span, self.db)
        return res

    @property
    def score(self):
        return self.identity

    @property
    def hit_length(self):
        return self.span

class kgXref(ABase):
    __tablename__ = "kgXref"

    kgID = Column(String, primary_key=True)

#    @declared_attr
#    def kgID(self):
#        return Column(String, ForeignKey('knownGene.name'), primary_key=True)


    def __repr__(self):
        return "%s(%s/%s)" % (self.__tablename__, self.geneSymbol, self.kgID)

    __str__ = __repr__

class knownGene(ABase):
    __tablename__ = "knownGene"

    __mapper_args__= {'always_refresh': False, 'exclude_properties': ['dist',
        '_dist']}

    __preload_classes__ = ("kgXref",)

    anno_cols = ("name", "distance", "feature")

    @declared_attr
    def name(cls):
        return Column(ForeignKey('kgXref.kgID'), primary_key=True)

    #@declared_attr
    #def kgXref(cls):
    #    #return relationship("kgXref", backref=backref("knownGene"), lazy="subquery")
#
#        return relationship(lambda: kgXref,
#                primaryjoin=lambda: knownGene.name==kgXref.kgID,
#            lazy="subquery")
            #viewonly=True)

    @property
    def name2(self):
        return self.kgXref.geneSymbol

    def link(self):
        l = "http://genome.ucsc.edu/cgi-bin/hgGene?hgg_gene=%s&db=%s"
        return l % (self.name, self.db)

    @property
    def protein(self):
        from toolshed import nopen
        l = "http://genome.ucsc.edu/cgi-bin/hgGene?hgg_do_getProteinSeq=1&hgg_gene="
        url = l + self.name
        seq = [x.strip() for x in nopen(url) if x.strip() and
                not ">" in x]
        return "".join(seq)

class all_mrna(ABase):
    __tablename__ = "all_mrna"

    qName = Column(String, unique=False, primary_key=True)

########NEW FILE########
__FILENAME__ = sequence
import urllib as U

__all__ = ('sequence', )

def _seq_from_xml(xml):
    start = xml.find(">", xml.find("<DNA")) + 1
    end = xml.rfind("</DNA>")
    return xml[start:end].replace(' ', '').replace('\n', '').strip()

def sequence(db, chrom, start, end):
    """
    return the sequence for a region using the UCSC DAS
    server. note the start is 1-based
    each feature will have it's own .sequence method which sends
    the correct start and end to this function.

    >>> sequence('hg18', 'chr2', 2223, 2230)
    'caacttag'
    """
    url = "http://genome.ucsc.edu/cgi-bin/das/%s" % db
    url += "/dna?segment=%s:%i,%i"
    xml = U.urlopen(url % (chrom, start, end)).read()
    return _seq_from_xml(xml)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = soup
from . import sqlsoup
from sqlalchemy import Table, util

class Genome(sqlsoup.SQLSoup):

    def map_to(self, attrname, tablename=None, selectable=None,
                    schema=None, base=None, mapper_args=util.immutabledict()):
        tbl = Table(tablename, self._metadata, autoload=True,
                 autoload_with=self.bind, schema=schema or self.schema)

        # make a fake primary key
        pids = [x for x in tbl.columns if x.name in ('chrom', 'chromStart', 'name',
                                                          'txStart', 'kgID')
                                       or x.primary_key or x.unique]
        if pids == []:
            pids = [x for x in tbl.columns if any(c in x.name.lower() for c in
                'chrom start name'.split())]
        models = __import__("cruzdb.models", globals(), locals(), [], -1).models
        try:
            base = getattr(models, tablename)
        except AttributeError:
            base = models.Feature

        mapper_args = dict(mapper_args)
        mapper_args['primary_key'] = pids
        return sqlsoup.SQLSoup.map_to(self, attrname, tablename, selectable,
                                       schema, base=base, mapper_args=mapper_args)

if __name__ == "__main__":
    db = Genome('mysql://genome@genome-mysql.cse.ucsc.edu/hg19')

    print(db.cpgIslandExt.first())
    print(db.refGene.first())


########NEW FILE########
__FILENAME__ = sqlsoup
"""

"""

from sqlalchemy import Table, MetaData, join
from sqlalchemy import schema, sql, util
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import scoped_session, sessionmaker, mapper, \
                            class_mapper, relationship, session,\
                            object_session, attributes
from sqlalchemy.orm.interfaces import MapperExtension, EXT_CONTINUE
from sqlalchemy.sql import expression

__version__ = '0.9.0'
__all__ = ['SQLSoupError', 'SQLSoup', 'SelectableClassType', 'TableClassType', 'Session']

Session = scoped_session(sessionmaker())
"""SQLSoup's default session registry.

This is an instance of :class:`sqlalchemy.orm.scoping.ScopedSession`,
and provides a new :class:`sqlalchemy.orm.session.Session`
object for each application thread which refers to it.

"""

class AutoAdd(MapperExtension):
    def __init__(self, scoped_session):
        self.scoped_session = scoped_session

    def instrument_class(self, mapper, class_):
        class_.__init__ = self._default__init__(mapper)

    def _default__init__(ext, mapper):
        def __init__(self, **kwargs):
            for key, value in kwargs.iteritems():
                setattr(self, key, value)
        return __init__

    def init_instance(self, mapper, class_, oldinit, instance, args, kwargs):
        session = self.scoped_session()
        state = attributes.instance_state(instance)
        session._save_impl(state)
        return EXT_CONTINUE

    def init_failed(self, mapper, class_, oldinit, instance, args, kwargs):
        sess = object_session(instance)
        if sess:
            sess.expunge(instance)
        return EXT_CONTINUE

class SQLSoupError(Exception):
    pass

class ArgumentError(SQLSoupError):
    pass

# metaclass is necessary to expose class methods with getattr, e.g.
# we want to pass db.users.select through to users._mapper.select
class SelectableClassType(type):
    """Represent a SQLSoup mapping to a :class:`sqlalchemy.sql.expression.Selectable`
    construct, such as a table or SELECT statement.
    
    """

    def insert(cls, **kwargs):
        raise SQLSoupError(
            'SQLSoup can only modify mapped Tables (found: %s)' \
              % cls._table.__class__.__name__
        )

    def __clause_element__(cls):
        return cls._table

    def __getattr__(cls, attr):
        if attr == '_query':
            # called during mapper init
            raise AttributeError()
        return getattr(cls._query, attr)

class TableClassType(SelectableClassType):
    """Represent a SQLSoup mapping to a :class:`sqlalchemy.schema.Table`
    construct.
    
    This object is produced automatically when a table-name
    attribute is accessed from a :class:`.SQLSoup` instance.
    
    """
    def insert(cls, **kwargs):
        o = cls()
        o.__dict__.update(kwargs)
        return o

    def relate(cls, propname, *args, **kwargs):
        """Produce a relationship between this mapped table and another
        one. 
        
        This makes usage of SQLAlchemy's :func:`sqlalchemy.orm.relationship`
        construct.
        
        """
        class_mapper(cls)._configure_property(propname, relationship(*args, **kwargs))
    def __getitem__(cls, key):
        return cls._query[key]


def _is_outer_join(selectable):
    if not isinstance(selectable, sql.Join):
        return False
    if selectable.isouter:
        return True
    return _is_outer_join(selectable.left) or _is_outer_join(selectable.right)

def _selectable_name(selectable):
    if isinstance(selectable, sql.Alias):
        return _selectable_name(selectable.element)
    elif isinstance(selectable, sql.Select):
        return ''.join(_selectable_name(s) for s in selectable.froms)
    elif isinstance(selectable, schema.Table):
        return selectable.name
    else:
        x = selectable.__class__.__name__
        if x[0] == '_':
            x = x[1:]
        return x

def _class_for_table(session, engine, selectable, base_cls, mapper_kwargs):
    selectable = expression._clause_element_as_expr(selectable)
    mapname = _selectable_name(selectable)
    # Py2K
    if isinstance(mapname, unicode): 
        engine_encoding = engine.dialect.encoding 
        mapname = mapname.encode(engine_encoding)
    # end Py2K

    if isinstance(selectable, Table):
        klass = TableClassType(mapname, (base_cls,), {})
    else:
        klass = SelectableClassType(mapname, (base_cls,), {})

    def _compare(self, o):
        L = list(self.__class__.c.keys())
        L.sort()
        t1 = [getattr(self, k) for k in L]
        try:
            t2 = [getattr(o, k) for k in L]
        except AttributeError:
            raise TypeError('unable to compare with %s' % o.__class__)
        return t1, t2

    # python2/python3 compatible system of 
    # __cmp__ - __lt__ + __eq__

    def __lt__(self, o):
        t1, t2 = _compare(self, o)
        return t1 < t2

    def __eq__(self, o):
        t1, t2 = _compare(self, o)
        return t1 == t2

    def __repr__(self):
        L = ["%s=%r" % (key, getattr(self, key, ''))
             for key in self.__class__.c.keys()]
        return '%s(%s)' % (self.__class__.__name__, ','.join(L))

    def __getitem__(self, key):
        return self._query[key]

    for m in ['__eq__', '__repr__', '__lt__', '__getitem__']:
        setattr(klass, m, eval(m))
    klass._table = selectable
    klass.c = expression.ColumnCollection()
    mappr = mapper(klass,
                   selectable,
                   extension=AutoAdd(session),
                   **mapper_kwargs)

    for k in mappr.iterate_properties:
        klass.c[k.key] = k.columns[0]

    klass._query = session.query_property()
    return klass

class SQLSoup(object):
    """Represent an ORM-wrapped database resource."""

    def __init__(self, engine_or_metadata, base=object, session=None):
        """Initialize a new :class:`.SQLSoup`.

        :param engine_or_metadata: a string database URL, :class:`.Engine` 
          or :class:`.MetaData` object to associate with. If the
          argument is a :class:`.MetaData`, it should be *bound*
          to an :class:`.Engine`.
        :param base: a class which will serve as the default class for 
          returned mapped classes.  Defaults to ``object``.
        :param session: a :class:`.ScopedSession` or :class:`.Session` with
          which to associate ORM operations for this :class:`.SQLSoup` instance.
          If ``None``, a :class:`.ScopedSession` that's local to this 
          module is used.

        """

        self.session = session or Session
        self.base=base

        if isinstance(engine_or_metadata, MetaData):
            self._metadata = engine_or_metadata
        elif isinstance(engine_or_metadata, (basestring, Engine)):
            self._metadata = MetaData(engine_or_metadata)
        else:
            raise ArgumentError("invalid engine or metadata argument %r" % 
                                engine_or_metadata)

        self._cache = {}
        self.schema = None

    @property
    def bind(self):
        """The :class:`sqlalchemy.engine.base.Engine` associated with this :class:`.SQLSoup`."""
        return self._metadata.bind

    engine = bind

    def delete(self, instance):
        """Mark an instance as deleted."""

        self.session.delete(instance)

    def execute(self, stmt, **params):
        """Execute a SQL statement.

        The statement may be a string SQL string,
        an :func:`sqlalchemy.sql.expression.select` construct, or a 
        :func:`sqlalchemy.sql.expression.text` 
        construct.

        """
        return self.session.execute(sql.text(stmt, bind=self.bind), **params)

    @property
    def _underlying_session(self):
        if isinstance(self.session, session.Session):
            return self.session
        else:
            return self.session()

    def connection(self):
        """Return the current :class:`sqlalchemy.engine.base.Connection` in use by the current transaction."""

        return self._underlying_session._connection_for_bind(self.bind)

    def flush(self):
        """Flush pending changes to the database.

        See :meth:`sqlalchemy.orm.session.Session.flush`.

        """
        self.session.flush()

    def rollback(self):
        """Rollback the current transction.

        See :meth:`sqlalchemy.orm.session.Session.rollback`.

        """
        self.session.rollback()

    def commit(self):
        """Commit the current transaction.

        See :meth:`sqlalchemy.orm.session.Session.commit`.

        """
        self.session.commit()

    def expunge(self, instance):
        """Remove an instance from the :class:`.Session`.

        See :meth:`sqlalchemy.orm.session.Session.expunge`.

        """
        self.session.expunge(instance)

    def expunge_all(self):
        """Clear all objects from the current :class:`.Session`.

        See :meth:`.Session.expunge_all`.

        """
        self.session.expunge_all()

    def map_to(self, attrname, tablename=None, selectable=None, 
                    schema=None, base=None, mapper_args=util.immutabledict()):
        """Configure a mapping to the given attrname.

        This is the "master" method that can be used to create any 
        configuration.

        :param attrname: String attribute name which will be
          established as an attribute on this :class:.`.SQLSoup`
          instance.
        :param base: a Python class which will be used as the
          base for the mapped class. If ``None``, the "base"
          argument specified by this :class:`.SQLSoup`
          instance's constructor will be used, which defaults to
          ``object``.
        :param mapper_args: Dictionary of arguments which will
          be passed directly to :func:`.orm.mapper`.
        :param tablename: String name of a :class:`.Table` to be
          reflected. If a :class:`.Table` is already available,
          use the ``selectable`` argument. This argument is
          mutually exclusive versus the ``selectable`` argument.
        :param selectable: a :class:`.Table`, :class:`.Join`, or
          :class:`.Select` object which will be mapped. This
          argument is mutually exclusive versus the ``tablename``
          argument.
        :param schema: String schema name to use if the
          ``tablename`` argument is present.


        """
        if attrname in self._cache:
            raise SQLSoupError(
                "Attribute '%s' is already mapped to '%s'" % (
                attrname,
                class_mapper(self._cache[attrname]).mapped_table
            ))

        if tablename is not None:
            if not isinstance(tablename, basestring):
                raise ArgumentError("'tablename' argument must be a string."
                                    )
            if selectable is not None:
                raise ArgumentError("'tablename' and 'selectable' "
                                    "arguments are mutually exclusive")

            selectable = Table(tablename, 
                                        self._metadata, 
                                        autoload=True, 
                                        autoload_with=self.bind, 
                                        schema=schema or self.schema)
        elif schema:
            raise ArgumentError("'tablename' argument is required when "
                                "using 'schema'.")
        elif selectable is not None:
            if not isinstance(selectable, expression.FromClause):
                raise ArgumentError("'selectable' argument must be a "
                                    "table, select, join, or other "
                                    "selectable construct.")
        else:
            raise ArgumentError("'tablename' or 'selectable' argument is "
                                    "required.")

        if not selectable.primary_key.columns and not \
                             'primary_key' in mapper_args:
            if tablename:
                raise SQLSoupError(
                            "table '%s' does not have a primary "
                            "key defined" % tablename)
            else:
                raise SQLSoupError(
                            "selectable '%s' does not have a primary "
                            "key defined" % selectable)

        mapped_cls = _class_for_table(
            self.session,
            self.engine,
            selectable,
            base or self.base,
            mapper_args
        )
        self._cache[attrname] = mapped_cls
        return mapped_cls


    def map(self, selectable, base=None, **mapper_args):
        """Map a selectable directly.

        The class and its mapping are not cached and will
        be discarded once dereferenced (as of 0.6.6).

        :param selectable: an :func:`.expression.select` construct.
        :param base: a Python class which will be used as the
          base for the mapped class. If ``None``, the "base"
          argument specified by this :class:`.SQLSoup`
          instance's constructor will be used, which defaults to
          ``object``.
        :param mapper_args: Dictionary of arguments which will
          be passed directly to :func:`.orm.mapper`.

        """

        return _class_for_table(
            self.session,
            self.engine,
            selectable,
            base or self.base,
            mapper_args
        )

    def with_labels(self, selectable, base=None, **mapper_args):
        """Map a selectable directly, wrapping the 
        selectable in a subquery with labels.

        The class and its mapping are not cached and will
        be discarded once dereferenced (as of 0.6.6).

        :param selectable: an :func:`.expression.select` construct.
        :param base: a Python class which will be used as the
          base for the mapped class. If ``None``, the "base"
          argument specified by this :class:`.SQLSoup`
          instance's constructor will be used, which defaults to
          ``object``.
        :param mapper_args: Dictionary of arguments which will
          be passed directly to :func:`.orm.mapper`.

        """

        # TODO give meaningful aliases
        return self.map(
                    expression._clause_element_as_expr(selectable).
                            select(use_labels=True).
                            alias('foo'), base=base, **mapper_args)

    def join(self, left, right, onclause=None, isouter=False, 
                base=None, **mapper_args):
        """Create an :func:`.expression.join` and map to it.

        The class and its mapping are not cached and will
        be discarded once dereferenced (as of 0.6.6).

        :param left: a mapped class or table object.
        :param right: a mapped class or table object.
        :param onclause: optional "ON" clause construct..
        :param isouter: if True, the join will be an OUTER join.
        :param base: a Python class which will be used as the
          base for the mapped class. If ``None``, the "base"
          argument specified by this :class:`.SQLSoup`
          instance's constructor will be used, which defaults to
          ``object``.
        :param mapper_args: Dictionary of arguments which will
          be passed directly to :func:`.orm.mapper`.

        """

        j = join(left, right, onclause=onclause, isouter=isouter)
        return self.map(j, base=base, **mapper_args)

    def entity(self, attr, schema=None):
        """Return the named entity from this :class:`.SQLSoup`, or 
        create if not present.

        For more generalized mapping, see :meth:`.map_to`.

        """
        try:
            return self._cache[attr]
        except KeyError, ke:
            return self.map_to(attr, tablename=attr, schema=schema)

    def __getattr__(self, attr):
        return self.entity(attr)

    def __repr__(self):
        return 'SQLSoup(%r)' % self._metadata


########NEW FILE########
__FILENAME__ = test_db
import unittest
from cruzdb import Genome
import os


class TestFeature(unittest.TestCase):
    """
    class to just use the mixin without a connection
    """
    def setUp(self):
        from cruzdb.models import Feature
        self.f = Feature()
        self.f.chrom = "chr1"
        self.f.txStart = 10
        self.f.txEnd = 61

        self.f.cdsStart = 29
        self.f.cdsEnd =  59
        """
        + exon
        | coding-exon
        _ UTR
        - intron

        10        20    26 29   34   39      47   52     59 61
        ++++++++++______+++|||||-----||||||||-----|||||||+++

        # introns = [(20, 26), (34, 39), (47, 52)]

        # coding introns = [(34, 39), (47, 52)]
        """
        self.f.exonStarts = "10,26,39,52,"
        self.f.exonEnds = "20,34,47,61,"

        self.strand = self.f.strand = '+'


    def test_localize_out_of_bounds(self):
        f = self.f
        #self.assertEqual(f.localize(0, 80), [None, None])
        self.assertEqual(f.localize(0, 80, 61, 60, cdna=True),
                                     [None, None, None, None])

        self.assertEqual(f.localize(0, 80, 61, 60, cdna=False),
                                    [None, None, None, 34])

    def test_localize_in_intron(self):
        f = self.f
        self.assertEqual(f.localize(34, cdna=True), None)

    def test_localize_cdsBounds(self):
        f = self.f
        self.assertEqual(f.localize(f.cdsStart, cdna=True), 0)
        # DOES THIS MAKE SENSE? if it's at cdsEnd, it's None
        self.assertEqual(f.localize(f.cdsEnd, cdna=True), None)

        l = sum(e - s for s, e in f.cds)
        self.assertEqual(f.localize(f.cdsEnd - 1, cdna=True), l - 1)

    def test_localize_txBounds(self):
        f = self.f
        self.assertEqual(f.localize(f.txStart, cdna=False), 0)
        # DOES THIS MAKE SENSE? if it's at cdsEnd, it's None
        self.assertEqual(f.localize(f.txEnd, cdna=False), None)

        l = sum(e - s for s, e in f.exons)
        self.assertEqual(f.localize(f.txEnd - 1, cdna=False), l - 1)

    def test_upstream(self):
        f = self.f
        u = f.upstream(10)
        self.assertEqual(u.end, f.start)
        self.assert_(u.is_upstream_of(f))

    def test_blat(self):
        try:
            import requests
        except ImportError:
            return
        g = Genome('hg18')
        f = g.refGene[19]
        f.chrom = "chr6"
        f.txStart = 135646802
        f.txEnd = 135646832
        r = list(f.blat())
        self.assert_(str(f.txStart) in repr(r), r)
        self.assert_(str(f.txEnd) in repr(r), r)


    def test_downstream(self):
        f = self.f
        u = f.downstream(10)
        self.assertEqual(f.end, u.start)
        self.assert_(u.is_downstream_of(f))
        u.chrom = "fake"
        self.assertEqual(None,  u.is_upstream_of(f))

class TestBasic(unittest.TestCase):
    def setUp(self):
        self.db = Genome('hg18')

    def testFirst(self):
        self.assert_(hasattr(self.db.refGene.first(), "txStart"))

    def test_bed_gene_pred(self):
        g = Genome('hg19')
        from sqlalchemy import and_
        from cStringIO import StringIO
        query = g.knownGene.filter(and_(g.knownGene.txStart > 10000, g.knownGene.txEnd < 20000))
        c = StringIO()
        Genome.save_bed(query, c)
        c.seek(0)
        rows = c.readlines()
        for toks in (row.split("\t") for row in rows):
            self.assert_(len(toks) == 12)
            self.assert_(int(toks[1]) > 10000)
            self.assert_(int(toks[2]) < 20000)

    def test_link(self):
        feat = self.db.knownGene.first()
        l = feat.link()

        self.assert_(l == "http://genome.ucsc.edu/cgi-bin/hgGene?hgg_gene=uc001aaa.2&db=hg18", l)



    def test_bed_other(self):
        g = self.db
        self.assertEqual(g.cpgIslandExt[12].bed(), 'chr1	829557	830482')
        self.assertEqual(g.cpgIslandExt[12].bed('length', 'perCpg'), 'chr1	829557	830482	925	17.9')


class TestGene(unittest.TestCase):
    def setUp(self):
        self.db = Genome('hg18')
        self.gene = self.db.refGene.filter_by(name2="MUC5B").first()

    def testExons(self):
        self.assert_(isinstance(self.gene.exons, list))
        self.assert_(self.gene.exons[0][0] >= self.gene.txStart)
        self.assert_(self.gene.exons[0][0] <= self.gene.cdsStart)

    def testIntrons(self):
        self.assert_(isinstance(self.gene.introns, list))
        self.assert_(self.gene.introns[0][0] >= self.gene.txStart)
        self.assert_(self.gene.introns[0][0] == self.gene.exons[0][1])
        self.assert_(all((s < e) for s, e in self.gene.introns))

    def testBed12(self):
        expected = "chr1	891739	900347	PLEKHN1,NM_032129	0	+	891774	899818	.	16	118,100,147,81,73,128,96,81,76,137,150,141,141,219,49,663,	0,207,3780,4024,4189,4382,4616,4827,5578,5791,6364,6689,7003,7336,7819,7945,"
        transcript = self.db.refGene.filter_by(name="NM_032129").first()
        self.assertEqual(transcript.bed12(), expected)

class TestDb(unittest.TestCase):
    def setUp(self):
        self.dba = Genome('hg18')
        self.dbb = Genome('hg19')

    def test_protein(self):

        g = self.dba.knownGene.filter_by(name="uc010ntk.1").first()
        prot = g.protein

        self.assert_(prot.startswith("MIITQTSHCYMTSLGILFLINILPGTTGQGESRRQEPGDFVKQDIG"), prot)
        self.assert_(prot.endswith("SAIKGMIRKQ"), prot)

    def test_ok(self):
        ga = self.dba.refGene.filter_by(name2="MUC5B").first()
        self.assert_(ga is not None)

    def test_repr(self):
        self.assert_("Genome" in repr(self.dba))
        self.assert_("hg18" in repr(self.dba))
        self.assert_("mysqldb" in repr(self.dba))

    def test_bins(self):
        bins = Genome.bins(12345, 56779)
        expected = set([1, 9, 73, 585])
        self.assertEqual(bins, expected)

    def test_tables(self):
        self.dba.refGene
        self.assert_("refGene" in self.dba.tables, self.dba.tables)

    def test_nearest(self):
        from cruzdb.models import Feature
        f = Feature()
        f.chrom = "chr1"
        f.txStart = 10
        f.txEnd = 61
        #db = Genome('hg18', host="localhost", user="brentp")
        db = self.dba
        self.assert_(db.refGene.first() is not None)
        self.assert_(db.refGene is not None)

        res = db.knearest(db.refGene, f, k=2)
        self.assert_(len(res) >= 2)

        f = db.refGene.first()
        key = (f.chrom, f.start, f.end, f.name)

        for k in (2, 4, 6):
            res = db.knearest("refGene", f, k=k)
            assert len(res) >= k
            self.assert_(key in ((n.chrom, n.start, n.end, n.name) for n in res),
                    (res, f))


        f = db.refGene.order_by(db.refGene.txStart).filter(db.refGene.c.strand == "+").first()
        assert f in db.upstream(db.refGene, f)

        down = db.downstream(db.refGene, f, k=10)
        self.assert_(len(down) >= 10)

        self.assert_(all(d.start >= f.start for d in down))


    def test_down_neg(self):
        db = self.dba
        fm = db.refGene.filter(db.refGene.c.strand == "-").first()
        down = db.downstream(db.refGene, fm, k=10)

        self.assert_(all(d.start <= fm.start for d in down))

    def test_dataframe(self):
        g = Genome('hg18')

        kg = g.dataframe('cpgIslandExt')
        self.assert_(kg.shape[0] == g.cpgIslandExt.count())

        q = g.cpgIslandExt.filter(g.cpgIslandExt.chromStart < 300000).limit(10)

        df = g.dataframe(q)
        self.assert_(df.shape[0] == 10)



    def test_mirror(self):

        try:
            os.unlink('/tmp/__u.db')
        except OSError:
            pass
        g = Genome('hg18')
        g.mirror(['chromInfo'], 'sqlite:////tmp/__u.db')
        a = str(g.chromInfo.filter().first())

        gs = Genome('sqlite:////tmp/__u.db')

        b = str(gs.chromInfo.filter().first())
        self.assertEqual(a, b)
        os.unlink('/tmp/__u.db')

    def tearDown(self):
        del self.dba

if __name__ == "__main__":
    unittest.main(failfast=True)

########NEW FILE########
__FILENAME__ = __main__
"""
use cruzdb to annotate an input file with tables from the corresponding
database. example usage:

    $ python -m cruzdb hg19 intervals.bed refGene dgv snp137Common wgEncodeRegTfbsClusteredV2

To annotate with the 4 tables. Output is to stdout.
"""

def annotate(input_bed, genome_version, tables, feature_strand=True,
        in_memory=False):
    from . import Genome
    Genome(genome_version).annotate(input_bed, tables,
            feature_strand=feature_strand, in_memory=in_memory)

def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__,
                   formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("genome", help="genome version to use (e.g. hg19)")
    p.add_argument("bed", help="input bed file to annotated")
    p.add_argument("--in-memory", default=False, action="store_true")

    p.add_argument('tables', nargs='*', help='tables to annotated with',
            default=['refGene', 'cpgIslandExt'])
    args = p.parse_args()

    if (args.genome is None or args.bed is None):
        sys.exit(not p.print_help())

    tables = args.tables or ('refGene', 'cpgIslandExt')
    annotate(args.bed, args.genome, tables, in_memory=args.in_memory)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# cruzdb documentation build configuration file, created by
# sphinx-quickstart on Thu Jul 11 16:22:31 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../..'))
print sys.path

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.todo',
'sphinx.ext.viewcode', 'sphinx.ext.autosummary', 'numpydoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

autosummary_generate = True
# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'cruzdb'
copyright = u'2013, Brent Pedersen'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5'
# The full version, including alpha/beta/rc tags.
release = '0.5'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

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

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'cruzdbdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'cruzdb.tex', u'cruzdb Documentation',
   u'Brent Pedersen', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'cruzdb', u'cruzdb Documentation',
     [u'Brent Pedersen'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'cruzdb', u'cruzdb Documentation',
   u'Brent Pedersen', 'cruzdb', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = lamina
import os.path as op
from toolshed import reader
from cruzdb import Genome

def lamina():
    if not op.exists('lamina.bed'):
        fh = open('lamina.bed', 'w')
        fh.write("#chrom\tstart\tend\tvalue\n")
        for gff in reader('http://www.nature.com/nature/journal/v453/n7197/extref/nature06947-s2.txt', header=False):
            fh.write("\t".join([gff[0], gff[3], gff[4], gff[5]]) + "\n")
        fh.close()
    return 'lamina.bed'

fname = 'supplement/Additional-File-11_lamina.anno.bed'
hg18 = Genome('sqlite:///hg18.db')
if not op.exists(fname):
    fhout = open(fname, 'w')
    hg18.annotate(lamina(), ('refGene', ), feature_strand=True, in_memory=True, parallel=True, out=fhout)
    fhout.close()


for cutoff in (0.90, 0.95):
    fh = open('/tmp/genes-%.2f.txt' % cutoff, 'w')
    for d in reader(fname):
        if float(d['value']) < cutoff: continue
        if d['refGene_distance'] == '0' or \
           d['refGene_distance'].startswith("0;"):
            print >>fh, "\n".join(d['refGene_name'].split(";"))
    fh.close()

cutoff = 0.90
fh = open('/tmp/genes-overlap-complete.txt', 'w')
for d in (l for l in reader(lamina()) if float(l['value']) > cutoff):
    if float(d['value']) < cutoff: continue

    start, end = map(int, (d['start'], d['end']))

    res = hg18.bin_query('refGene', d['chrom'], start, end).all()

    if len(res) == 0: continue

    for r in res:
        # genes completely contained within an LAD
        if start <= r.start and end >= r.end:
            print >>fh, r.gene_name

########NEW FILE########
__FILENAME__ = plot-timing
import pandas as pa
import sys
import matplotlib
matplotlib.rc('font', **{'family': 'serif', 'serif': ['Times']})
matplotlib.rc('text', **{'usetex': 'true'})
from matplotlib import pyplot as plt
import numpy as np

plt.close()
f, ax = plt.subplots(1, figsize=(3, 3))

df = pa.read_table(sys.argv[1])

pf = df.ix[~df.parallel]
pt = df.ix[df.parallel]


ax.set_ylabel('Intervals / Second')

x = 0.1 + np.arange(3)
width = 0.35


rects0 = ax.bar(x, 3327. / pt.time, width, color='0.70', alpha=0.91)

rects1 = ax.bar(x[:len(pf.time)] + width + 0.03, 3327. / pf.time, width,
        color='0.3', alpha=0.91)

ax.set_xticks(x + width)
ax.set_ylim(0, (3327. / min(pf.time)) + 50)
ax.set_xticklabels(["%s\n%s" % tup for tup in zip(pt['loc'], pt.instance)], 
        fontsize='x-small')

legend = ax.legend((rects0[0], rects1[0]), ('parallel', 'not-parallel'))


plt.setp(legend.get_texts(), fontsize='x-small')
plt.setp(ax.get_yticklabels(), fontsize='x-small')
plt.subplots_adjust(right=0.98, left=0.17, top=0.98, bottom=0.12)

plt.savefig('manuscript-latex/figure1.eps')
plt.savefig('manuscript-latex/figure1.pdf')
plt.savefig('figure1.pdf')

########NEW FILE########
__FILENAME__ = Additional-File-2-code-example
from cruzdb import Genome
from cruzdb.sequence import sequence

# mirror the neede tables from UCSC to a local sqlite db
local = Genome('hg19').mirror(('refGene', 'targetScanS'), 'sqlite:///hg19.mirna.db')

# connect to the newly created local sqlite database instance.
refseq_ids = []

# iterate over the coding in refGene
for gene in (rgene for rgene in local.refGene if rgene.is_coding):

    if None in gene.utr3: continue # skip genes with no UTR

    utr_start, utr_end = gene.utr3
    # query the targetScan miRNA table with efficient bin query 
    sites = local.bin_query('targetScanS', gene.chrom, utr_start, utr_end)

    # print BED file of genes whose 3'UTR contains a miR-96 target site
    # with a score > 85.
    if any("miR-96" in s.name and s.score > 85 for s in sites):
        refseq_ids.append(gene.name) # save the refSeq for later GO analysis

        # gene is a python object but its string representation is BED format
        # we also print out the UTR sequence.
        print gene, sequence('hg19', gene.chrom, utr_start, utr_end)

# open a webbrowser to show enrichment of the genes we've selected in DAVID
Genome.david_go(refseq_ids)

########NEW FILE########
__FILENAME__ = timing

from cruzdb import Genome
import time
from toolshed import nopen
import os

anno_file = "data_c_constant_early.bed"
# sub-sample to get fewer rows.
list(nopen("|awk 'NR == 1 || NR % 4 == 0'" +(" %s > %s.some" % (anno_file, anno_file))))
anno_file += ".some"
nlines = sum(1 for _ in nopen(anno_file))

print "loc\tinstance\tparallel\ttime"
for parallel in (True, False):
    for name, args in (('local\tsqlite', ('sqlite:///hg18.db',)),
                       ('remote\tmysql', ('hg18',)),
                       ('local\tmysql', ('hg18', 'brentp', 'localhost'))
                       ):
        g = Genome(*args)

        out = "%s-%s.anno.txt" % (name.replace("\t", "-"), parallel)

        t0 = time.time()
        g.annotate(anno_file, ('refGene',), out=out, feature_strand=True,
                parallel=parallel)
        t1 = time.time()
        print "\t".join(map(str, (name, parallel, ("%.1f" % (t1 - t0)))))
        assert nlines == sum(1 for _ in nopen(out))
        os.unlink(out)

########NEW FILE########
__FILENAME__ = interval_tree
import operator
"""
simple version of an interval tree that cannot be updated after creation.
"""

class IntervalTree(object):
    __slots__ = ('intervals', 'left', 'right', 'center')

    def __init__(self, intervals, depth=12, minbucket=48, _extent=None, maxbucket=512):
        """
        `intervals` a list of intervals *with start and end* attributes.
        `depth`     the depth of the tree
        `minbucket` if any node in the tree has fewer than minbucket
                    elements, make it a leaf node
        `maxbucket` even it at specifined `depth`, if the number of intervals >
                    maxbucket, split the node, make the tree deeper.

        depth and minbucket usually do not need to be changed. if
        dealing with large numbers (> 1M) of intervals, the depth could
        be increased to 24.

        Usage:

         >>> ivals = [Interval(2, 3), Interval(1, 8), Interval(3, 6)]
         >>> tree = IntervalTree(ivals)
         >>> sorted(tree.find(1, 2))
         [Interval(2, 3), Interval(1, 8)]

        this provides an extreme and satisfying performance improvement
        over searching manually over all 3 elements in the list (like
        a sucker).

        the IntervalTree class supports the iterator protocol
        so it's easy to loop over all elements in the tree:

         >>> import operator
         >>> sorted([iv for iv in tree], key=operator.attrgetter('start'))
         [Interval(1, 8), Interval(2, 3), Interval(3, 6)]


        any object with start and end attributes can be used
        in the incoming intervals list.
        """

        depth -= 1
        if (depth == 0 or len(intervals) < minbucket) and len(intervals) < maxbucket:
            self.intervals = intervals
            self.left = self.right = self.center = None
            return

        if _extent is None:
            # sorting the first time through allows it to get
            # better performance in searching later.
            intervals.sort(key=operator.attrgetter('start'))

        left, right = _extent or \
               (intervals[0].start, max(i.end for i in intervals))
        #center = intervals[len(intervals)/ 2].end
        center = (left + right) / 2.0

        self.intervals = []
        lefts, rights  = [], []

        for interval in intervals:
            if interval.end < center:
                lefts.append(interval)
            elif interval.start > center:
                rights.append(interval)
            else: # overlapping.
                self.intervals.append(interval)

        self.left   = lefts  and IntervalTree(lefts,  depth, minbucket, (intervals[0].start,  center)) or None
        self.right  = rights and IntervalTree(rights, depth, minbucket, (center,               right)) or None
        self.center = center


    def find(self, start, end):
        """find all elements between (or overlapping) start and end"""
        if self.intervals and not end < self.intervals[0].start:
            overlapping = [i for i in self.intervals if i.end >= start
                                                    and i.start <= end]
        else:
            overlapping = []

        if self.left and start <= self.center:
            overlapping += self.left.find(start, end)

        if self.right and end >= self.center:
            overlapping += self.right.find(start, end)

        return overlapping

    def __iter__(self):
        if self.left:
            for l in self.left: yield l

        for i in self.intervals: yield i

        if self.right:
            for r in self.right: yield r

class Interval(object):
    __slots__ = ('start', 'end', 'chrom')
    def __init__(self, start, end, chrom=None):
        self.start = start
        self.end  = end
        self.chrom = chrom
    def __repr__(self):
        return "Interval(%i, %i)" % (self.start, self.end)

if __name__ == '__main__':

    def brute_force_find(intervals, start, end):
        return [i for i in intervals if i.end >= start and i.start <= end]

    import random, time
    def rand():
        s = random.randint(1, 2000000)
        return Interval(s, s + random.randint(200, 6000))
    intervals = [rand() for i in xrange(300000)]
    START, STOP = 390000, 400000
    intervals.append(Interval(0, 500000))
    tries = 100


    tree = IntervalTree(intervals)
    t = time.time()
    for i in range(tries):
        res = tree.find(START, STOP)
    treetime = time.time() - t
    t = time.time()
    print treetime

    #"""

    for i in range(tries):
        bf = [i for i in intervals if i.end >= START and i.start <= STOP]
    btime = time.time() - t
    assert not set(bf).symmetric_difference(res) , (len(bf), len(res), set(bf).difference(res), START, STOP)
    print treetime, btime, btime/treetime


    assert sum(1 for x in tree) == len(intervals), "iterator not working?"

    intervals = [rand() for i in xrange(300)]
    atree = IntervalTree(intervals)
    import cPickle
    btree = cPickle.loads(cPickle.dumps(atree, -1))

    af = atree.find(START, STOP)
    bf = btree.find(START, STOP)
    assert len(af) == len(bf)
    for a, b in zip(af, bf):
        assert a.start == b.start
        assert a.end == b.end


    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = nearest_and_bins
"""
"testing" of bin queries and nearest queries
take a long time to run so not part of standard test suite
"""

import time
from cruzdb import Genome
from random import randrange, seed

#g = Genome('hg18', host='localhost', user='brentp')

#g.mirror(['refGene'], "sqlite:////tmp/u.db")


g = Genome('sqlite:////tmp/u.db')



# if we choose a huge distance all should have a distance of 0
#assert all(k.dist == 0  for k in  g.knearest("refGene", "chr1", 1234, 9915555, k=3))


print g.upstream("refGene", "chr1", 9444, 9555, k=6)

last = g.refGene.order_by(-g.refGene.table().c.txStart)[0]
print last
last.txStart = 1000 + last.txEnd
last.txEnd = last.txStart + 100
last.strand = "-"
print last
print g.upstream("refGene", last, k=6)

1/0


seed(1)

istart = 12345
iend = 386539

qall = list(g.refGene.all())

#while True:
for iend in (randrange(istart, 65555555) for i in range(100)):


    t = time.time()
    q = g.bin_query('refGene', 'chr1', istart, iend)
    a = list(q)
    print len(a)
    print time.time() - t

    #"""
    t = time.time()
    refGene = g.refGene


    rg = refGene.table()
    q = g.session.query(rg).filter(rg.c.chrom == "chr1", rg.c.txStart
            <= iend, rg.c.txEnd >= istart)
    q = refGene.filter(rg.c.chrom == "chr1", rg.c.txStart
            <= iend, rg.c.txEnd >= istart)
    b = list(q)
    print len(b)

    print time.time() - t
    #"""

    t = time.time()
    b = [r for r in g.refGene.all() if r.chrom == "chr1" and r.txStart <= iend and r.txEnd >= istart]
    #print(len(qall))
    #b = [r for r in qall if (r.chrom == "chr1" and r.txStart <= iend and r.txEnd >= istart)]
    print time.time() - t

    assert len(a) == len(b), (len(a), len(b), iend)
    print

########NEW FILE########
__FILENAME__ = time_tree
import sys
sys.path.extend([".", "scripts", "cruzdb"])
import operator
import random
from interval_tree import Interval, IntervalTree
from intersecter import Intersecter
import time


N=500000
TRIES = 10
START, STOP = 0, 20000

def rands(n=N, len_range=(200, 16000), start_max=STOP):

    def rand():
        start = random.randint(1, start_max)
        return Interval(start, start + random.randint(*len_range))

    return [rand() for i in xrange(n)]


def brute_force_find(intervals, start, end):
    return [i for i in intervals if i.end >= start and i.start <= end]

def search(tree, start, end, tries):

    t0 = time.time()
    lens = []
    if isinstance(tree, list):
        for i in range(tries):
            res = brute_force_find(tree, start, end)
            res.sort(key=operator.attrgetter('start'))
            lens.append("%i:%s" % (len(res), [x.start for x in res[-1:]]))
            #lens.append(len(res))
    else:
        for i in range(tries):
            res = tree.find(start, end)
            res.sort(key=operator.attrgetter('start'))
            lens.append("%i:%s" % (len(res), [x.start for x in res[-1:]]))
            #lens.append(len(res))
    t1 = time.time()
    return res, t1 - t0, lens


start_max = STOP * 3
while True:
    intervals = rands(N, start_max = start_max)
    t0 = time.time()
    tree = IntervalTree(intervals)
    t1 = time.time()
    print "time to build IntervalTree with %i intervals: %.3f" % (N, t1 - t0)
    t0 = time.time()
    ints = Intersecter(intervals)
    t1 = time.time()
    print "time to build Intersector with %i intervals: %.3f" % (N, t1 - t0)

    found, t, tree_lens = search(tree, START, STOP, TRIES)
    print "time to search tree %i times: %.3f. found %i intervals" % (TRIES, t, len(found))

    found, t, brute_lens = search(intervals, START, STOP, TRIES)
    print "time to search brute %i times: %.3f. found %i intervals" % (TRIES, t, len(found))

    found, t, inter_lens = search(ints, START, STOP, TRIES)
    print "time to search intersecter %i times: %.3f. found %i intervals" % (TRIES, t, len(found))

    for tl, bl, il in zip(tree_lens, brute_lens, inter_lens):
        assert tl == bl == il, (tl, bl, il)
    print
    #start_max *= 2

########NEW FILE########
