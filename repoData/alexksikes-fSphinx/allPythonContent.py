__FILENAME__ = cache
"""This module adds caching to Sphinx."""

__all__ = ['RedisCache', 'CacheSphinx', 'CacheIO']

import redis
import hashlib
import simplejson as json

from sphinxapi import SphinxClient


class RedisCache(object):
    """Creates a cache using Redis which can be attached to a fSphinx client.
    """
    def __init__(self, **kwargs):
        # default is 200MB
        self.maxmemory = kwargs.pop('maxmemory', 1024 * 1024 * 200)
        # default is volatile-lru cf http://antirez.com/post/redis-as-LRU-cache.html
        self.maxmemory_policy = kwargs.pop('maxmemory_policy', 'volatile-lru')
        # default is 3 samples
        self.maxmemory_samples = kwargs.pop('maxmemory_samples', 3)
        # expire on new keys default is we let maxmemory-policy do the job
        self.expire = kwargs.pop('expire', 10 ** 10)
        # initialize redis cache
        self.c = redis.StrictRedis(**kwargs)
        self.c.config_set('maxmemory', self.maxmemory)
        self.c.config_set('maxmemory-policy', self.maxmemory_policy)
        self.c.config_set('maxmemory-samples', self.maxmemory_samples)

    def _MakeKey(self, key):
        if not isinstance(key, basestring):
            key = repr(key)
        return hashlib.md5(key).hexdigest()

    def Set(self, key, value, expire=0, _raw=False):
        if not _raw:
            key = self._MakeKey(key)
            value = json.dumps(value)
        self.c.set(key, value)

        expire = expire or self.expire
        if expire == -1:
            self.c.persist(key)
        else:
            self.c.expire(key, expire)

    def Get(self, key):
        value = self.c.get(self._MakeKey(key))
        if value:
            value = json.loads(value)
        return value

    def GetSet(self, key, func):
        if key in self:
            val = self.Get(key)
        else:
            val = func()
            self.Set(key, val)
        return val

    def Dumps(self, to_file):
        to_file = open(to_file, 'w')
        for k in self.c.keys('*'):
            to_file.write('%s@@@@@%s\n' % (k, self.c.get(k)))

    def Loads(self, from_file, expire=0):
        for l in open(from_file):
            if '@@@@@' not in l:
                print 'Warning: skipping %s' % l
            k, v = l.split('@@@@@')
            self.Set(k, v, expire, _raw=True)

    def Flush(self):
        self.c.flushdb()

    def __contains__(self, key):
        return self.c.exists(self._MakeKey(key))


def CacheSphinx(cache, cl):
    """Caches the request of a Sphinx client.
    """
    # there are requests and to be computed results
    reqs = [req for req in cl._reqs]
    results = [None] * len(reqs)
    comp_reqs = []
    comp_results = []

    # get results from cache
    for i, req in enumerate(reqs):
        if req in cache:
            results[i] = cache.Get(req)
            results[i]['time'] = 0
        else:
            comp_reqs.append(req)

    # get results that need to be computed
    if comp_reqs:
        cl._reqs = comp_reqs
        comp_results = SphinxClient.RunQueries(cl)
    else:
        cl._reqs = []

    # return None on IO failure
    if comp_results == None:
        return None

    # cache computed results and Get results
    for req, result in zip(comp_reqs, comp_results):
        if result != None:
            cache.Set(req, result)
        results[results.index(None)] = result

    return results


def CacheIO(func):
    """Decorator used to memoize the return value of an instance method.
    The instance is assumed to have a RedisCache.
    """
    # assumes object has a redis cache
    def Wrapper(self, *args, **kwargs):
        key = (func.__name__, args, kwargs)

        def Lazy():
            return func(self, *args, **kwargs)
        if hasattr(self, 'cache') and isinstance(self.cache, RedisCache):
            return self.cache.GetSet(key, Lazy)
        else:
            return Lazy()
    return Wrapper

########NEW FILE########
__FILENAME__ = facets
"""This module adds facet computation to Sphinx."""

__all__ = ['Facet', 'FacetGroup']

import sphinxapi
import weakref

import utils
from hits import DBFetch
from hits import DB

try:
    import cache
except ImportError:
    cache = None


class Facet(object):
    """Creates a new facet of a given "facet_name".

    The facet must have a corresponding attribute declared in the Sphinx conf.
    The attribute may be either single or multi-valued and its name defaults to
    "facet_name_attr".

    Suppose we had a director facet, the attribute would look like this:

    # needed to create the director facet
    sql_attr_multi =
        uint director_attr from query;
        select imdb_id, imdb_director_id from directors

    Additionaly there must be a corresponding MySQL table (except for numerical
    facets) which maps ids to terms.
    The MySQL name defaults to "facet_name_terms" with an id and "facet_name"
    column.

    Again the director table terms would look like this:

    select * from director_terms limit 5;
    +----+------------------+
    | id | director         |
    +----+------------------+
    |  5 | Ingmar Bergman   |
    | 19 | Federico Fellini |
    | 33 | Alfred Hitchcock |
    | 36 | Buster Keaton    |
    | 37 | Gene Kelly       |
    +----+------------------+

    If the facet values are numerical (for example to refine by year) such a table
    isn't needed and sql_table = None must be explicitely passed.

    There are a lot of optional keyword arguments which are mainly used to
    overwrite the defaults:

    sql_table: name of the corresponsing MySQL table
    (defaults to "facet_name_terms").

    sql_col: name of the column field (defaults to "facet_name").
    sql_query: the full SQL query which will be called to retrieve the facet terms.

    attr: name of the corresponding Sphinx attribute (defaults to "facet_name_attr").
    func: grouping function (defaults to sphinxapi.SPH_GROUPBY_ATTR).
    group_sort: group sorting function (defaults to @count).
    sph_field: name of the corresponding Sphinx search field (defaults to "name")

    order_by: a lambda function used to order the returned facet values.
    max_num_values: maximum number of facet values (defaults 15).
    cutoff: threshold amount of matches to stop computing (defaults to 0)
    augment: augment the number of facet values if one is selected (defaults False).
    """
    def __init__(self, name, **kwargs):
        self.name = name

        # sql parameters
        self._sql_col = kwargs.get('sql_col', name)
        self._sql_table = kwargs.get('sql_table', name + '_terms')
        if self._sql_table:
            sql_query = \
                'select %s from %s ' % (self._sql_col, self._sql_table) + \
                'where id in ($id) order by field(id, $id)'
        else:
            sql_query = None
        self._sql_query = kwargs.get('sql_query', sql_query)

        # sphinx variables
        self._attr = kwargs.get('attr', self._sql_col + '_attr')
        self._func = kwargs.get('func', sphinxapi.SPH_GROUPBY_ATTR)
        self._group_sort = kwargs.get('group_sort', '@count desc')
        self._set_select = kwargs.get('set_select', '@groupby, @count')
        self._sph_field = kwargs.get('sph_field', name)

        # facets variables
        self._id = kwargs.get('id', name)
        self._enable = kwargs.get('enable', True)
        self._order_by = kwargs.get('order_by', lambda v: v['@term'])
        self._order_by_desc = False
        self._max_num_values = kwargs.get('max_num_values', 15)
        self._cutoff = kwargs.get('cutoff', 0)
        self._matches = kwargs.get('matches', 0)
        self._augment = kwargs.get('augment', True)

        # sphinx and db clients
        cl = kwargs.get('cl')
        if cl:
            self._cl = weakref.ref(cl)()
        self._db = kwargs.get('db')

        self._InitResults()

    def _InitResults(self):
        # the returning values
        self.results = utils.storage(time=0, total_found=0, error='', warning='', matches=[])
        self.query = ''

    def AttachSphinxClient(self, cl, db=None):
        """Attach a SphinxClient and a database to perform the computation and
        to retrieve the results from the database.

        If the facet terms are numerical, db is optional.
        """
        self._cl = cl
        self._db = db or self._db or cl.db_fetch._db or DB

    def SetGroupBy(self, attr, func, group_sort='@count desc'):
        """Set grouping attribute, function and grouping sorting clause.

        attr must refer to the facet attribute as declared in your Sphinx config file.
        More info: http://sphinxsearch.com/docs/manual-2.0.1.html#api-func-setgroupby.
        """
        self._attr = attr
        self._func = func
        self._group_sort = group_sort or self._group_sort

    def SetGroupSort(self, group_sort='@count desc'):
        """Set group sorting close.

        Note that this must be a clause not a custom grouping function.
        """
        self._group_sort = group_sort

    def SetGroupFunc(self, group_func, alias='@groupfunc', order='desc'):
        """Set a custom group sorting function.

        The value of the function is in '@groupfunc' or specified by the alias.
        """
        self._set_select = '@groupby, @count, %s as %s' % (group_func, alias)
        self._group_sort = '%s %s' % (alias, order)

    def SetOrderBy(self, key, order='desc'):
        """Set the ordering of the returned facet values.

        Possible ordering could be by '@count', '@groupby' or '@groupfunc'.
        """
        self._order_by = lambda v: v[key]
        self._order_by_desc = (order == 'desc')

    def SetMaxNumValues(self, max_num_values):
        """Set the maximum number of facet values returned.
        """
        self._max_num_values = max_num_values

    def SetCutOff(self, cutoff):
        """Set threshold amount of matches to stop computing.

        More info: http://sphinxsearch.com/docs/manual-2.0.1.html#api-func-setlimits
        """
        self._cutoff = cutoff

    def SetAugment(self, augment):
        """Set whether to compute one more facet value if a facet value is already selected.
        """
        self._augment = augment

    def Compute(self, query):
        """Compute the facet for a given query.

        query could be a string or MultifieldQuery object.
        """
        if self._enable:
            self._Prepare(query, self._cl)
            results = self._cl.RunQueries()[0]
            self._SetValues(query, results, self._db)
            self._OrderValues()
        else:
            self._InitResults()

    def SetEnable(self, enable=True):
        """A facet could be enabled / disabled meaning that it will or will not be computed.
        """
        self._enable = enable

    def _Prepare(self, query, cl):
        """Used internally to prepare the facet for computation for a given query
        using a given SphinxClient.
        """
        def SaveSphinxOpts():
            return utils.save_attrs(cl,
                ['_offset', '_limit', '_cutoff', '_select', '_groupby',
                 '_groupfunc', '_groupsort'])

        def LoadSphinxOpts(opts):
            utils.load_attrs(cl, opts)

        if self._augment:
            more = query.count(self._sph_field)
        else:
            more = 0
        self.query = query

        opts = SaveSphinxOpts()
        cl.SetLimits(0, self._max_num_values + more, cutoff=self._cutoff)
        cl.SetSelect(self._set_select)
        cl.SetGroupBy(self._attr, self._func, self._group_sort)
        cl.AddQuery(getattr(query, 'sphinx', query))
        LoadSphinxOpts(opts)

    def _SetValues(self, query, sphinx_results, db):
        """Used internally to set the facet terms and additional values in this facet.
        """
        # reset the facet values and stats
        self.results = utils.storage(time=0, total_found=0, error='', warning='', matches=[])
        
        # fetch the facet terms from the db
        db_fetch = DBFetch(db, self._sql_query, getter=lambda x: x['attrs']['@groupby'])
        hits = db_fetch.Fetch(sphinx_results)
        
        # let's get the stats from the results
        for k in self.results.keys():
            if k != 'matches':
                self.results[k] = hits[k]

        # finally let's setup the facet values
        for match in hits.matches:
            # get all virtual attributes
            value = dict((k, v) for k, v in match['attrs'].items() if k.startswith('@'))
            # get the facet term
            value['@term'] = match['@hit'][match['@hit'].keys()[-1]]
            # get the value of the grouping func
            value['@groupfunc'] = value.get('@groupfunc', value['@count'])
            # and whether the facet has been selected
            value['@selected'] = '@%s %s' % (self._sph_field, value['@term']) in query
            # append each value
            self.results.matches.append(value)

    def _OrderValues(self):
        """Used internally to order the facet values returned.
        """
        self.results.matches = sorted(self, key=self._order_by, reverse=self._order_by_desc)

    def __str__(self):
        """A string representation of this facet showing the number of results,
        time taken and the facet values returned.
        """
        stats = '(%s/%s values group sorted by "%s" in %s sec.)' % (
            self._max_num_values, self.results.total_found, self._group_sort, self.results.time)
        s = '%s: %s\n' % (self.name, stats)
        for i, value in enumerate(self):
            s += '\t%s. %s, ' % (i + 1, value['@term'])
            s += '@count=%s, @groupby=%s' % (value['@count'], value['@groupby']) + ', '
            s += ', '.join('%s=%s' % (k, v) for k, v in value.items()
                if k not in ['@term', '@count', '@groupby']) + '\n'
        return s.encode('utf-8')

    def __iter__(self):
        """Iterate over the computed facet values only.
        """
        for v in self.results.matches:
            yield v


class FacetGroup(object):
    """A FacetGroup is a set of facets which is used for performance and caching.

    Only one query to searchd is performed.
    Caching is performed using a fSphinx client with a RedisCache attached.
    """
    def __init__(self, *facets, **kwargs):
        # facet variables
        self.facets = facets
        self.time = 0
        self.query = ''
        self.cache = None

        # sphinx variables
        cl = kwargs.get('cl')
        db = kwargs.get('db', DB)
        if cl or db:
            self.AttachSphinxClient(cl, db)

    def AttachSphinxClient(self, cl, db=None):
        """Attach a SphinxClient and a database to perform the computation and
        to retrieve the results from the database.

        If all the facets are numerical, db is optional.
        """
        self._cl = cl
        self._db = db or self._db or cl.db_fetch._db or DB

    def AttachCache(self, cache):
        """Attach a RedisCache to cache the facet computation.
        """
        self.cache = cache

    def Compute(self, query, caching=None):
        """Compute all the facet in this gorup for a given query.

        query could be a string or MultifieldQuery object.
        """
        self._Prepare(query)
        results = self._RunQueries(caching)
        self._SetValues(query, results)

    def GetFacet(self, facet_id):
        for f in self.facets:
            if f._id == facet_id:
                return f

    def SetFacetEnable(self, facet_id, enable=True):
        """Enable / disable the computation of a given facet.
        """
        self.GetFacet(facet_id).SetEnable(enable)

    def _Prepare(self, query):
        """Used internally to prepare all the facets in this group for computation
        for a given query.
        """
        self.time = 0
        for f in self.facets:
            if f._enable:
                f._Prepare(query, self._cl)
            else:
                f._InitResults()
        self.query = query

    def _RunQueries(self, caching=None):
        """Used internally to run the queries all at once and possibly perform caching.

        If set the caching parameter is set to False, caching never occurs.
        """
        if not self.cache or caching is False:
            # it could still be cached if cl has a cache ..
            if hasattr(self._cl, 'cache'):
                return self._cl.RunQueries(caching)
            else:
                return self._cl.RunQueries()
        else:
            return cache.CacheSphinx(self.cache, self._cl)

    def _SetValues(self, query, results):
        """Used internally to set all the facet terms and additional values in the facets
        in this group.
        """
        for f in self.facets:
            if f._enable:
                f._SetValues(query, results.pop(0), self._db)
                f._OrderValues()
                self.time += float(f.results.time)

    def __len__(self):
        return len(self.facets)

    def __str__(self):
        """A string representation all of the facets in the group.
        """
        s = 'facets: (%s facets in %s sec.)\n' % (len(self.facets), self.time)
        for i, f in enumerate(self.facets):
            s += '%s. %s' % (i + 1, f)
        return s[:-1]

    def __iter__(self):
        """Iterate over the facets of the group.
        """
        for f in self.facets:
            yield f

########NEW FILE########
__FILENAME__ = hits
"""A MySQL read only storage layer for Sphinx to retrieve hits."""

__all__ = ['Hits', 'DBFetch', 'DB', 'SplitOnSep', 'BuildExcerpts', 'Highlight']

from operator import itemgetter
import utils

DB = None


class DBFetch(object):
    """Creates a DBFetch object to retrieve hits from the database.

    The sql parameter is a SQL statement with the special variable $id which
    will be replaced by the ids that Sphinx returns.
    The db parameter is a handle to your database created with utils.database.

    # let's have a handle to our fsphinx database
    db = utils.database(dbn='mysql', db='fsphinx', user='fsphinx', passwd='fsphinx')

    # let's create a fetcher
    db_fetch = DBFetch(db, sql =
    '''select
        imdb_id, filename, title, year, plot,
        (select group_concat(distinct director_name separator '@#@') from directors as d
        where d.imdb_id = t.imdb_id) as directors
    '''

    Addtionnally functions to post process the hits could be added.
    """
    def __init__(self, db=DB, sql='', getter=itemgetter('id'), post_processors=[]):
        self._db = db
        self._sql = sql
        self._getter = getter
        self._post_processors = post_processors

    def _FetchInternal(self, hits):
        ids = [self._getter(m) for m in hits.matches]
        if ids:
            s_ids = ','.join(map(str, ids))
            if not self._sql:
                values = (utils.storage(id=str(id)) for id in ids)
            else:
                values = self._db.query(self._sql.replace('$id', s_ids))
            for value, match in zip(values, hits.matches):
                match['@hit'] = value
            for p in self._post_processors:
                p(hits)
        hits.ids = ids

    def Fetch(self, sphinx_results):
        """Returns a Hits object for the given Sphinx results.
        """
        return Hits(sphinx_results, self)


class Hits(utils.storage):
    """Returned by DBFetch or create an empty Hits object.

    A Hits object behaves like a normal sphinx results but each match has an additional
    field called "@hit" for each field value retrieved.
    """
    def __init__(self, sphinx_results=None, db_fetch=None):
        utils.storage.__init__(self,
            dict(status=0, time=0, total=0, total_found=0, error='', warning='', matches=[],
                 fields=[], words=[], ids=[], attrs=[]))
        if sphinx_results:
            self.update(sphinx_results)
        if self['warning']:
            print self['warning']
        if self['error']:
            raise Exception(self['error'])
        if not db_fetch:
            db_fetch = DBFetch(None, '', getter=itemgetter('id'))
        db_fetch._FetchInternal(self)

    def __str__(self):
        """A string representation of these hits showing the number of results,
        time taken and the hits retrieved.
        """
        s = 'matches: (%(total)i/%(total_found)i documents in %(time)s sec.)\n' % self
        for i, match in enumerate(self['matches']):
            s += '%s. ' % (i + 1)
            s += 'document=%(id)s, weight=%(weight)s\n' % match
            s += ', '.join('%s=%s' % (k, utils._unicode(v))
                for k, v in match['attrs'].items()) + '\n'
            for k, v in match['@hit'].items():
                if isinstance(v, list):
                    v = ', '.join(v)
                s += '\t%s=%s\n' % (k, utils._unicode(v))
        s += '\nwords:\n'
        for i, word in enumerate(self['words']):
            s += '%s. ' % (i + 1)
            s += '"%(word)s": %(docs)s documents, %(hits)s hits\n' % word
        return s.encode('utf-8')

    def __iter__(self):
        """Iterate over every match only.
        """
        for match in self.matches:
            yield match


class SplitOnSep(object):
    """A post processor to split multi value fields which have concatenated using a
    separator.
    """
    def __init__(self, *on_fields, **opts):
        self._on_fields = on_fields
        self._suffix = opts.get('suffix', '')
        self._sep = opts.get('sep', '@#@')

    def __call__(self, hits):
        for match in hits.matches:
            hit = match['@hit']
            for f in self._on_fields:
                if isinstance(hit[f], basestring):
                    hit[f + self._suffix] = hit[f].split(self._sep)


class BuildExcerpts(object):
    """A post processor to build excerpts using Sphinx BuildExcerpts function.
    """
    def __init__(self, cl, *on_fields, **opts):
        self._cl = cl
        self._on_fields = on_fields
        self._suffix = opts.get('suffix', '_excerpts')
        self._index = opts.get('index', getattr(cl, 'default_index', '*'))
        self._opts = opts
        #self._opts['query_mode'] = opts.get('query_mode', True)

    def __call__(self, hits):
        words = getattr(self._cl.query, 'sphinx', self._cl.query)

        docs = []
        for match in hits.matches:
            docs.extend([utils._unicode(match['@hit'][f]) for f in self._on_fields])

        all_excerpts = self._cl.BuildExcerpts(docs, self._index, words, self._opts)
        print all_excerpts
        for match, excerpts in zip(hits.matches, utils.group(all_excerpts, len(self._on_fields))):
            for f, excerpt in zip(self._on_fields, excerpts):
                match['@hit'][f + self._suffix] = excerpt or match['@hit'][f]


class Highlight(BuildExcerpts):
    """A post processor to highlight the results returned.
    """
    def __init__(self, cl, *on_fields, **opts):
        opts['suffix'] = opts.get('suffix', '_highlighted')
        opts['limits'] = 2048
        BuildExcerpts.__init__(self, cl, *on_fields, **opts)

########NEW FILE########
__FILENAME__ = pretty_url
"""This module is used to transform a query into a nice url and vice versa."""

__all__ = ['PrettyUrlToQuery', 'QueryToPrettyUrl']

import urlparse
import urllib
import re
import utils

PATH_PATTERN = re.compile('(\w+)=([^/]+)|([^/]+)')


def QueryToPrettyUrl(query, root='', keep_order=True, **kwargs):
    """Takes a query either as a string or a MultiFiedQuery object and returns
    a pretty url.

    Additional url query parameters could be also specified. The order of the
    query terms is returned as a url query parameter of name "ot".
    """
    if isinstance(query, basestring):
        from queries import MultiFieldQuery
        query = MultiFieldQuery(query)
    # create the path of the url
    url = {}
    for qt in query:
        f = qt.user_field
        if not f in url:
            if f == '*':
                url[f] = ''
            else:
                url[f] = '%s=' % f
        else:
            url[f] += '|'
        status = (qt.status == '-') and '*' or ''
        url[f] += '%s%s' % (status, qt.term)
    url = '%s/' % '/'.join(url[k] for k in sorted(url.keys()))
    # handle keeping the order of the queries
    order = ''
    if keep_order:
        order = [(i, qt.user_field) for i, qt in enumerate(query)]
        order = [x[0] for x in sorted(order, key=lambda x: x[1])]
        order = ''.join(map(str, order))
    if len(order) > 1:
        kwargs['ot'] = order
    # keep other parameters being passed
    url = utils.urlquote_plus(url, safe='/|*=')
    if kwargs:
        url += '?' + urllib.urlencode(kwargs, doseq=True)

    return urlparse.urljoin(root, url)


def PrettyUrlToQuery(url, root='', order=''):
    """Transforms a pretty url into a query.

    The order of the query terms is given using a url query parameter of name "ot"
    or by explicitely using the order variable.
    """
    root = root.split('/')
    url = urlparse.urlparse(url)
    path = utils.unquote_plus(url.path)
    # make the query string from url
    query = []
    for field, terms, all in PATH_PATTERN.findall(path):
        if all and all not in root:
            terms = all
            field = '*'
        if not terms:
            continue
        for term in terms.split('|'):
            if term[0] == '*':
                status = '-'
                term = term[1:]
            else:
                status = ''
            query.append('(@%s%s %s)' % (status, field, term))
    # handle the order of the query terms
    if not order:
        order = re.search('(?:\?|&|^)ot=(\d+)', url.query)
        order = order and order.group(1)
    if order:
        order = dict((q, int(i)) for q, i in zip(query, order))
        query = sorted(query, key=lambda x: order.get(x, 0))

    return ' '.join(qt for qt in query)

########NEW FILE########
__FILENAME__ = queries
"""An advanced multi-field query object for Sphinx."""

__all__ = ['MultiFieldQuery', 'QueryTerm', 'QueryParser']

import copy
import re
import utils

QUERY_PATTERN = re.compile('''
    @(?P<status>[+-]?)(?P<field>\w+|\*)\s+(?P<term>[^@()]+)
    |
    (?P<all>[^@()]+)''',
    re.I | re.U | re.X)


def ChangeQuery(func):
    def Wrapper(self, query):
        if isinstance(query, basestring):
            query = MultiFieldQuery(query, user_sph_map=self.user_sph_map)
        elif isinstance(query, QueryTerm):
            query_term = copy.deepcopy(query)
            query = MultiFieldQuery(user_sph_map=self.user_sph_map)
            query.AddQueryTerm(query_term)
        return func(self, query)
    return Wrapper


def ChangeQueryTerm(func):
    def Wrapper(self, query_term):
        if isinstance(query_term, basestring):
            query_term = QueryTerm.FromString(query_term, user_sph_map=self.user_sph_map)
        return func(self, query_term)
    return Wrapper


class QueryParser(object):
    """Creates a query parser of the given type. Returns a ParsedQuery.
    """
    def __init__(self, type, **kwargs):
        self.type = type
        self.kwargs = kwargs

    def Parse(self, query):
        q = self.type(**self.kwargs)
        q.Parse(query)
        return q
        

class MultiFieldQuery(object):
    """Creates multi-field query to let the user search within specific fields
    and therefore refine by facet values.

    The dictionnary user_sph_map provides a mapping between the user field search
    and the sphinx field search.

    If passed to a sphinx client, match mode be set to extended2 as shown below:

    # setting cl to extended matching mode
    cl.SetMatchMode(sphinxapi.SPH_MATCH_EXTENDED2)

    The class variable ALLOW_EMPTY controls whether to interpret an empty query
    as '' leading Sphinx to full scan mode.
    """

    ALLOW_EMPTY = False

    def __init__(self, query='', user_sph_map={}):
        self.user_sph_map = dict((k.lower(), v.lower()) for k, v in user_sph_map.items())
        self._qts = []
        if query:
            self.Parse(query)

    def Parse(self, query):
        """Parse a query string.

        Every query passed to a facet or to a sphinx client must have been parsed
        beforehand.
        """
        self._qts = []
        for m in QUERY_PATTERN.finditer(query):
            query_term = QueryTerm.FromMatchObject(m, self.user_sph_map)
            if query_term:
                self.AddQueryTerm(query_term)

    @ChangeQueryTerm
    def AddQueryTerm(self, query_term):
        """Used internally to add a query term as a QueryTerm object.
        """
        if query_term in self:
            self._qts.remove(query_term)
        if query_term:
            self._qts.append(query_term)

    @ChangeQueryTerm
    def RemoveQueryTerm(self, query_term):
        """Used internally to remove a query term as a QueryTerm object.
        """
        if query_term in self:
            self._qts.remove(query_term)

    @property
    def user(self):
        """A representation of this query as manipulated by the user.
        """
        return ' '.join(qt.user for qt in self)

    @property
    def sphinx(self):
        """The string representation of this query which should be sent to sphinx.
        """
        s = utils.strips(' '.join(qt.sphinx for qt in self))
        if s == '(@* "")':
            s = ''
        if not s and not self.ALLOW_EMPTY:
            s = ' '
        return s

    @property
    def uniq(self):
        """A canonical / unique string representation of this query.
        """
        return utils.strips(' '.join(qt.uniq for qt in sorted(self)))

    def count(self, field):
        """Returns a count of how many times this field appears is in the query.
        """
        return sum(1 for qt in self if (field.lower() in (qt.user_field, qt.sph_field) and qt.status != '-'))

    @ChangeQueryTerm
    def __getitem__(self, query_term):
        if isinstance(query_term, int):
            return self._qts[query_term]
        return self._qts[self._qts.index(query_term)]

    @ChangeQueryTerm
    def __contains__(self, query_term):
        return query_term in self._qts

    def __iter__(self):
        """Iterates over query terms in order.
        """
        for qt in self._qts:
            yield qt

    def __str__(self):
        return self.user

    def __repr__(self):
        return repr(self._qts)

    @ChangeQuery
    def __and__(self, query):
        q = self - self  # hack to permit subclassing
        for query_term in query:
            if query_term in self and query_term in query:
                q.AddQueryTerm(query_term)
        return q

    @ChangeQuery
    def __or__(self, query):
        return self + query

    @ChangeQuery
    def __sub__(self, query):
        q = copy.deepcopy(self)
        for query_term in query:
            q.RemoveQueryTerm(query_term)
        return q

    @ChangeQuery
    def __add__(self, query):
        q = copy.deepcopy(self)
        for query_term in query:
            q.AddQueryTerm(query_term)
        return q

    def __len__(self):
        return len(self._qts)

    @ChangeQueryTerm
    def GetQueryToggle(self, query_term):
        query = copy.deepcopy(self)
        query[query_term].Toggle()
        return query

    def GetQueryFilter(self, ffilter):
        query = self - self  # permit subclassing
        for qt in self:
            if ffilter(qt):
                query.AddQueryTerm(qt)
        return query

    def ToPrettyUrl(self, **kwargs):
        from pretty_url import QueryToPrettyUrl
        return QueryToPrettyUrl(self, **kwargs)


class QueryTerm(object):
    """Used internally by a multi-field query.

    Query terms may be created from a match object or its string representation.
    """
    def __init__(self, status, field, term, user_sph_map={}):
        self.status = status
        self.term = utils.strips(term)
        field = field.strip().lower()
        self.user_field = utils.dictreverse(user_sph_map).get(field, field).lower()
        self.sph_field = user_sph_map.get(field, field).lower()

    @classmethod
    def FromMatchObject(cls, m, user_sph_map={}):
        """Create a QueryTerm from a match object.
        """
        if not m:
            return None
        status, field, term, all = m.groups()
        if all and not all.strip():
            return None
        if all:
            term, field = all, '*'
        if status != '-':
            status = ''
        if field.strip():
            return cls(status, field, term, user_sph_map)

    @classmethod
    def FromString(cls, s, user_sph_map={}):
        """Create a QueryTerm from a string.
        """
        m = QUERY_PATTERN.search(s)
        return cls.FromMatchObject(m, user_sph_map)

    @property
    def user(self):
        """A representation of this query term as manipulated by the user.
        """
        return '(@%s%s %s)' % (self.status, self.user_field, self.term)

    @property
    def sphinx(self):
        """The string representation of this query term which should be sent to
        sphinx.
        """
        # bug in sphinx: make science-fiction -> science fiction
        term = re.sub('(\w)(-)(\w)', '\\1 \\3', self.term, re.U)
        if self.status in ('', '+'):
            return '(@%s %s)' % (self.sph_field, term)
        else:
            return ''

    @property
    def uniq(self):
        """A canonical / unique string representation of this query term.
        """
        return self.sphinx.strip().lower()

    def __str__(self):
        return self.user

    def __repr__(self):
        return '<%s>' % vars(self)

    def __cmp__(self, qt):
        """Two query terms are considered equal case insensitively of their term
        value.
        """
        return cmp((self.user_field, self.term.lower()), (qt.user_field, qt.term.lower()))

    def __hash__(self):
        """Used by MultiFieldQuery.__contains__.
        """
        return hash((self.user_field, self.term.lower()))

    def Toggle(self):
        self.status = self.status != '-' and '-' or ''

    def ToggleOn(self):
        self.status = ''

    def ToggleOff(self):
        self.status = '-'

########NEW FILE########
__FILENAME__ = sphinx
"""Provides all the functionalities of fSphinx into on client."""

__all__ = ['FSphinxClient']

import os
import sys
import weakref

import utils
from sphinxapi import SphinxClient
from facets import FacetGroup
from facets import Facet
from hits import Hits
import cache


# NOTE: batch queries with AddQuery and RunQueries are not implemented.

class FSphinxClient(SphinxClient):
    def __init__(self):
        """Creates a sphinx client but with all of fSphinx additional functionalities.
        """
        # the possible options
        self.query_parser = None
        self.default_index = '*'
        self.db_fetch = None
        self.cache = None
        self.sort_mode_options = []

        # the returned results
        self.query = ''
        self.hits = Hits()
        self.facets = FacetGroup()

        SphinxClient.__init__(self)

    def AttachQueryParser(self, query_parser):
        """Attach a query parser so every query will be parsed using it.
        """
        self.query_parser = query_parser

    def AttachDBFetch(self, db_fetch):
        """Attach a DBFetch object to retrieve hits from the database.
        """
        self.db_fetch = db_fetch

    def AttachFacets(self, *facets, **kwargs):
        """Attach a list of facet which will be computed.

        The facets are put into a FacetGroup for performance.
        """
        # if not found get db from db_fetch
        db = kwargs.get('db')
        if not db and hasattr(self, 'db_fetch'):
            db = self.db_fetch._db

        # avoid memory leak and circular references to cl
        cl = kwargs.get('cl')
        if not cl:
            cl = weakref.proxy(self)

        # set the facets and the Sphinx client
        self.facets = FacetGroup(*facets)
        self.facets.AttachSphinxClient(cl, db)

    def AttachCache(self, cache):
        """Attach a RedisCache to cache the results.

        If facets are attached, this will also cache the facets.
        """
        self.cache = cache

    def SetDefaultIndex(self, index):
        """Sets a default index so we don't have to pass it to Query each time.

        By default Sphinx searches all indexes served by searchd.
        """
        self.default_index = index

    def SetSortModeOptions(self, options, reset=True):
        if reset:
            self.sort_mode_options = options
        else:
            self.sort_mode_options.update(options)

    def SetSortMode(self, mode, clause=''):
        if mode in self.sort_mode_options:
            sort_mode = self.sort_mode_options[mode]
        else:
            sort_mode = (mode, clause)
        SphinxClient.SetSortMode(self, *sort_mode)

    def RunQueries(self, caching=None):
        if not self.cache or caching is False:
            return SphinxClient.RunQueries(self)
        else:
            return cache.CacheSphinx(self.cache, self)

    def Query(self, query, index='', comment=''):
        """Processes the query as Sphinx normally would.

        If specified, parse the query, retrieve the hits and compute the facets.
        """
        # first let's parse the query if possible
        if self.query_parser and isinstance(query, basestring):
            query = self.query_parser.Parse(query)
        self.query = query

        # check the default index
        index = index or self.default_index

        # let's perform a normal query
        results = SphinxClient.Query(self, getattr(query, 'sphinx', query), index, comment)
     
        # let's fetch the hits from the DB if possible
        if self.db_fetch and results and results['total_found']:
            self.hits = self.db_fetch.Fetch(results)
        else:
            self.hits = Hits(results)

        # let's compute the facets if possible
        if self.facets and results and results['total_found']:
            self.facets.Compute(query)

        # keep expected return of SphinxClient
        return self.hits

    @classmethod
    def FromConfig(cls, path):
        """Creates a client from a config file.

        A configuration file is a plain python file which creates a client
        called "cl" in its local namespace.
        """
        # if path is a module
        if hasattr(path, '__file__'):
            path = os.path.splitext(path.__file__)[0] + '.py'

        for d in utils.get_all_sub_dirs(path)[::-1]:
            sys.path.insert(0, d)
        cf = {'sys':sys}; execfile(path, cf, cf)
        return cf['cl']

    def Clone(self, memo={}):
        """Creates a copy of this client.

        This makes sure a new connection is not reiniated on the db and to the cache.
        It will also initialize the returned results (query, hits, facet results).
        """
        return self.__deepcopy__(memo)

    def __deepcopy__(self, memo):
        cl = self.__class__()

        attrs = utils.save_attrs(self,
            [a for a in self.__dict__ if a not in ['query', 'hits', 'facets', 'db_fetch', 'cache']])
        utils.load_attrs(cl, attrs)

        if self.db_fetch:
            cl.AttachDBFetch(self.db_fetch)

        if self.facets:
            facets = []
            for f in self.facets:
                attrs = utils.save_attrs(f,
                    [a for a in f.__dict__ if a not in ['_db', 'results', 'query']])
                f = Facet(f.name)
                utils.load_attrs(f, attrs)
                facets.append(f)
            cl.AttachFacets(*facets)

        if self.cache:
            cl.AttachCache(self.cache)

        return cl

########NEW FILE########
__FILENAME__ = utils
import codecs
import copy
import re
import urllib
import os

import web
from web.utils import *
database = web.database


def _unicode(s):
    if isinstance(s, unicode):
        pass
    elif isinstance(s, str):
        s = s.decode('utf-8')
    else:
        s = str(s).decode('utf-8')
    return s


def utf8(s):
    if isinstance(s, str):
        pass
    elif isinstance(s, unicode):
        s = s.encode('utf-8')
    return s


def strips(s, chars=' '):
    return re.sub('(%s){2,}' % chars, chars, s).strip()


def get_all_sub_dirs(path):
    paths = []
    d = os.path.dirname(path)
    while d not in ('', '/'):
        paths.append(d)
        d = os.path.dirname(d)
    if '.' not in paths:
        paths.append('.')
    return paths


def save_attrs(obj, attr_names):
    return dict((k, copy.deepcopy(v)) for k, v in obj.__dict__.items() if k in attr_names)


def load_attrs(obj, attrs):
    for k, v in attrs.items():
        if k in obj.__dict__:
            obj.__dict__[k] = v

unquote_plus = urllib.unquote_plus


def listify(obj):
    if not isinstance(obj, list):
        obj = [obj]
    return obj

try:
    from collections import OrderedDict
except ImportError:
    try:
        from collective.ordereddict import OrderedDict
    except ImportError:
        OrderedDict = dict


def urlquote_plus(val, safe='/'):
    if val is None: return ''
    if not isinstance(val, unicode): val = str(val)
    else: val = val.encode('utf-8')
    return urllib.quote_plus(val, safe)


def open_utf8(path):
    bom = codecs.BOM_UTF8.decode('utf8')
    f = codecs.open(path, encoding='utf8')
    l = f.readline()

    if l.startswith(bom):
        yield l.lstrip(bom)
    else:
        yield l
    for l in f:
        yield l


def iterfsep(path, idx=[], sep='\t'):
    for l in open_utf8(path):
        v = l.split(sep)
        v[-1] = v[-1].strip()
        if idx:
            v = [v[i] for i in idx]
        yield v

########NEW FILE########
__FILENAME__ = bug.groupfunc
﻿# This bug has been fixed as of Sphinx 2.0.2-beta (r3019) thanks

from __init__ import *

# sql_table is optional and defaults to facet_name_terms
factor = Facet('actor', sql_table='actor_terms')

# the sphinx client is what will perform the computation
factor.AttachSphinxClient(cl, db)

# setting up a custom sorting function
factor.SetGroupFunc('avg(nb_votes_attr*user_rating_attr)')

# let's set the number of facet values (defaults to 15)
factor.SetMaxNumValues(1)

factor.Compute('drama')
print factor

# sql_table is optional and defaults to facet_name_terms
fyear = Facet('year', sql_table=None)

# the sphinx client is what will perform the computation
fyear.AttachSphinxClient(cl, db)

# setting up a custom sorting function
fyear.SetGroupFunc('avg(100*user_rating_attr)')

# let's set the number of facet values (defaults to 15)
fyear.SetMaxNumValues(1)

fyear.Compute('drama')
print fyear

# let's build a Sphinx Client
cl = sphinxapi.SphinxClient()

# assuming searchd is running on 9315
cl.SetServer('localhost', 9315)

# let's put the facets in a group for faster computation
facets = FacetGroup(factor, fyear)

# as always Sphinx is what carries the computation
facets.AttachSphinxClient(cl, db)

facets.Compute('drama')
print facets
########NEW FILE########
__FILENAME__ = bug.setselect
﻿# This bug has been fixed as of Sphinx 2.0.2-beta (r3019) thanks

# submitted: http://sphinxsearch.com/bugs/view.php?id=792

# Suppose you have an index with an attribute called user_rating_attr with value between 0 and 1.

import sphinxapi

# let's build a Sphinx Client
cl = sphinxapi.SphinxClient()

# assuming searchd is running on 9315
cl.SetServer('localhost', 9315)
cl.SetLimits(0, 1)

query = 'movie'

# Each query run separately

print 'one query at a time'
cl.SetSelect('user_rating_attr, 1*user_rating_attr as @score')
print cl.Query(query)['matches']

# [{'id': 56687L, 'weight': 1L, 'attrs': {'@score': 0.80000001192092896, 'user_rating_attr': 0.80000001192092896}}]

# The score is 0.80 as expected

cl.SetSelect('user_rating_attr, 100*user_rating_attr as @score')
print cl.Query(query)['matches']

# [{'id': 56687L, 'weight': 1L, 'attrs': {'@score': 80.0, 'user_rating_attr': 0.80000001192092896}}]

# The score is 80 as expected

# These are the same queries but run in batch with RunQueries.

print 'all queries at once'
cl.SetSelect('user_rating_attr, 1*user_rating_attr as @score')
cl.AddQuery(query)
cl.SetSelect('user_rating_attr, 100*user_rating_attr as @score')
cl.AddQuery(query)
results = cl.RunQueries()

print results[0]['matches']
print results[1]['matches']

# [{'id': 56687L, 'weight': 1L, 'attrs': {'@score': 80.0, 'user_rating_attr': 0.80000001192092896}}]
# [{'id': 56687L, 'weight': 1L, 'attrs': {'@score': 80.0, 'user_rating_attr': 0.80000001192092896}}]

# The score is 80 for both !!!
########NEW FILE########
__FILENAME__ = test_facets
from __init__ import *

## Playing with Facets

# sql_table is optional and defaults to (facet_name)_terms
factor = Facet('actor', sql_table='actor_terms')

# the sphinx client is what will perform the computation
factor.AttachSphinxClient(cl, db)

# let's set the number of facet values returned to 5
factor.SetMaxNumValues(5)

# computing the actor facet for the query "drama"
factor.Compute('drama')

# let's see how this looks like
print factor

# setting up a custom sorting function
factor.SetGroupFunc('sum(user_rating_attr * nb_votes_attr)')

# @groupfunc holds the value of the custom grouping function
factor.SetOrderBy('@groupfunc', order='desc')

# computing the actor facet for the query "drama"
factor.Compute('drama')

# let's what we get
print factor

# sql_table is optional and defaults to (facet_name)_terms
fyear = Facet('year', sql_table=None)

# let's put the facets in a group for faster computation
facets = FacetGroup(fyear, factor)

# as always Sphinx is what carries the computation
facets.AttachSphinxClient(cl, db)

# finally compute these two facets at once
facets.Compute("drama", caching=False)

# turning caching on
facets.AttachCache(cache)

# computing facets twice with caching on
facets.Compute('drama')
facets.Compute('drama')
assert(facets.time == 0)

# this makes sure the facet computation is not fetched from the cache
facets.Compute('drama', caching=False)
assert(facets.time > 0)
########NEW FILE########
__FILENAME__ = test_hits
from __init__ import *

## Retrieving Results

# let's fetch the results from the DB
db_fetch = DBFetch(db, sql = 
'''select 
    imdb_id, filename, title, year, plot,    
    (select group_concat(distinct director_name separator '@#@') from directors as d 
    where d.imdb_id = t.imdb_id) as directors
    from titles as t 
    where imdb_id in ($id)
    order by field(imdb_id, $id)
''')

# let's perform a simple query
results = cl.Query('movie')

# and fetch the results form the DB
hits = db_fetch.Fetch(results)

# looking at the hits
print hits

# make sure directors are returned as a list instead of as a concatenated string
db_fetch.post_processors = [SplitOnSep('directors', sep='@#@')]
########NEW FILE########
__FILENAME__ = test_pretty_url
from __init__ import *

# we start with the following user query
query = 'movie @year 1999 @-genre drama (@actor harrison ford)'

# and transform the query into a pretty url 
# result should be: movie/actor=harrison+ford/genre=*drama/year=1999/?ot=0321
url = QueryToPrettyUrl(query)
print url

# and now back to a user query
print PrettyUrlToQuery(url)

# try with url parameters
url = QueryToPrettyUrl(query, root='/search/', keep_order=True, s=0, so='relevance')
print url

# and back to a user query
print PrettyUrlToQuery(url, root='/search/')

# some more ...
print QueryToPrettyUrl('movie', root='/search/')

url = 'author=Arjan+Durresi/keyword=networks|systems/?ot=201'
print PrettyUrlToQuery(url, root='/search/')
########NEW FILE########
__FILENAME__ = test_queries
from __init__ import *

# sql_table is optional and defaults to (facet_name)_terms
factor = Facet('actor', sql_table='actor_terms')

# the sphinx client is what will perform the computation
factor.AttachSphinxClient(cl, db)

# let's set the number of facet values returned to 5
factor.SetMaxNumValues(5)

## Playing With Multi-field Queries

# let's create a query parser to parse multi-field queries
query_parser = QueryParser(MultiFieldQuery, user_sph_map={'actor':'actors', 'genre':'genres'})

# parsing a multi-field query
query = query_parser.Parse('@year 1999 @genre drama @actor harrison ford')

# the query the user will see: '(@year 1999) (@genre drama) (@actor harrison ford)'
print query.user

# the query that should be passed to Sphinx: '(@genres drama) (@actors harrison ford)'
print query.sphinx

# let's toggle the year field off
query['@year 1999'].ToggleOff()

# the query the user will see: '(@-year 1999) (@genre drama) (@actor harrison ford)'
print query.user

# the query that should be sent to sphinx: '(@genres drama) (@actors harrison ford)'
print query.sphinx

# is the query term '@year 1999' in query
assert('@year 1999' in query)

# a connical form of this query: (@actors harrison ford) (@genres drama)
print query.uniq

# a unique url path representing this query: /actor/harrison+ford/genre/drama/year/*1999/?ot=210
print query.ToPrettyUrl()

# setting cl to extended matching mode
cl.SetMatchMode(sphinxapi.SPH_MATCH_EXTENDED2)

# and now passing a multi-field query object
factor.Compute(query)

# and looking at the results
print factor
########NEW FILE########
__FILENAME__ = test_simsearch
from __init__ import *

## Full text search is fine, how about item based search!

# we assume you have SimSearch configured 
from config import simsearch_config

# and wrap cl to give it similarity search abilities
cl = simsearch_config.cl.Wrap(cl)

# looking for movies similar to Terminator (movie id = 88247)
cl.Query('(@similar 88247) movie')
########NEW FILE########
__FILENAME__ = test_sphinx
from __init__ import *

# let's fetch the results from the DB
db_fetch = DBFetch(db, sql = 
'''select 
    imdb_id, filename, title, year, plot,    
    (select group_concat(distinct director_name separator '@#@') from directors as d 
    where d.imdb_id = t.imdb_id) as directors
    from titles as t 
    where imdb_id in ($id)
    order by field(imdb_id, $id)
''')

# sql_table is optional and defaults to (facet_name)_terms
fyear = Facet('year', sql_table=None)

# sql_table is optional and defaults to (facet_name)_terms
factor = Facet('actor', sql_table='actor_terms')

# the sphinx client is what will perform the computation
factor.AttachSphinxClient(cl, db)

# let's set the number of facet values returned to 5
factor.SetMaxNumValues(5)

# creating a multi-field query parser
query_parser = QueryParser(MultiFieldQuery, user_sph_map={
    'genre' : 'genres', 
    'actor' : 'actors'
})

# parsing the query 
query = query_parser.Parse('@year 1999 @genre drama @actor harrison ford')

## Putting Everything Together

# creating a sphinx client
cl = FSphinxClient()

# it behaves exactly like a normal SphinxClient
cl.SetServer('localhost', 9315)

# get the results from the db
cl.AttachDBFetch(db_fetch)

# attach the facets
cl.AttachFacets(fyear, factor)

# running the query
cl.Query('movie')

# or pass a MultiFieldQuery
cl.Query(query)
    
## Playing With Configuration Files

# create a fSphinx client from a configuration file
cl = FSphinxClient.FromConfig('./tutorial/config/sphinx_config.py')

# querying for "movie"
hits = cl.Query('movie')

print hits
########NEW FILE########
__FILENAME__ = preload_cache
#! /usr/bin/env python

import sys
import getopt

from fsphinx import FSphinxClient


def run(query, depth, flush, to_file, from_file, opts):
    cl = get_sphinx_client(opts)
    if flush:
        cl.cache.Flush()
    if from_file:
        cl.cache.Loads(from_file)
    else:
        preload_facets(query, depth, opts)
    if to_file:
        cl.cache.Dumps(to_file)


def get_sphinx_client(opts):
    cl = FSphinxClient.FromConfig(opts['conf'])
    # this must be the same as in th search
    cl.SetLimits(0, 10)
    # wait for no more than chosen minute
    cl.SetConnectTimeout(opts['timeout'])
    # set the expire on all keys which will be inserted
    cl.cache.expire = opts['expire']

    return cl


def preload_facets(query, depth, opts):
    # have we reached maximum depth
    if depth < 0: return
    else: depth -=1
    # create a new sphinx client each time
    cl = get_sphinx_client(opts)
    # allow full scan mode
    if cl.query_parser:
        query = cl.query_parser.Parse(query)
        query.ALLOW_EMPTY = True
    # let's compute the query
    print 'query = %s ...' % query,
    cl.Query(query)
    print '%s sec.' % cl.hits['time']
    # and also do it for each facet and recurse
    for f in cl.facets:
        for i, v in enumerate(f):
            preload_facets('%s (@%s %s)' % (query, f._sph_field, v['@term']), depth, opts)


def usage():
    print 'Usage:'
    print '    python preload_cache.py [options] start_query'
    print
    print 'Description:'
    print '    Load the cache with facets of start_query and any queries found in these facets.'
    print
    print 'Options:'
    print '    -c, --conf <sphinx_config>  : path to config file (default is ./sphinx_config.py)'
    print '    -d, --depth <int>           : maximum depth to go'
    print '    -f, --flush                 : flush the cache beforehand'
    print '    --dump <tofile>             : also dump the results to a file'
    print '    --load <fromfile>           : load the results from a dumped file'
    print '    --expire <int>              : expire flag on loaded keys in seconds (default -1 no expire)'
    print '    -h, --help                  : this help message'
    print
    print 'Email bugs/suggestions to Alex Ksikes (alex.ksikes@gmail.com)'


def main():
    try:
        _opts, args = getopt.getopt(sys.argv[1:], 'c:d:fh',
            ['conf=', 'depth=', 'flush', 'timeout=', 'dump=', 'load=',
             'expire=', 'help'])
    except getopt.GetoptError:
        usage(); sys.exit(2)

    query, depth, flush = args and args[0], 1, False
    to_file, from_file = '', ''
    opts = dict(conf='sphinx_config.py', timeout=60.0, expire=-1)
    for o, a in _opts:
        if o in ('-q', '--query'):
            query = a
        if o in ('-c', '--conf'):
            opts['conf'] = a
        elif o in ('-d', '--depth'):
            depth = int(a)
        elif o in ('-f', '--flush'):
            flush = True
        elif o in ('--timeout'):
            opts['timeout'] = float(a)
        elif o in ('--dump_file'):
            to_file = a
        elif o in ('--load_file'):
            from_file = a
        elif o in ('--expire'):
            opts['expire'] = int(a)
        elif o in ('-h', '--help'):
            usage(); sys.exit()

    if len(args) < 1:
        usage()
    else:
        run(query, depth, flush, to_file, from_file, opts)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = search
#! /usr/bin/env python

import sys
import getopt

import fsphinx


def run(query, conf, offset=0, limit=1, max_results=1000):
    cl = fsphinx.FSphinxClient.FromConfig(conf)
    cl.SetLimits(offset, limit, max_results)
    cl.Query(query)

    if hasattr(cl, 'query'):
        print 'query:\n%s\n' % cl.query
    if hasattr(cl, 'hits'):
        print cl.hits
    if hasattr(cl, 'facets'):
        print cl.facets


def usage():
    print 'Usage:'
    print '    python search.py [options] query'
    print
    print 'Description:'
    print '    This program (CLI search) is for testing and debugging purposes only.'
    print
    print 'Options:'
    print '    -c, --conf              : path to config file (default is ./sphinx_config.py)'
    print '    -o, --offset int        : (default is 0)'
    print '    -l, --limit  int        : (default is 1)'
    print '    -h, --help              : this help message'
    print
    print 'Email bugs/suggestions to Alex Ksikes (alex.ksikes@gmail.com)'


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:o:l:h',
            ['conf=', 'offset=', 'limit=', 'help'])
    except getopt.GetoptError:
        usage(); sys.exit(2)

    conf = 'sphinx_config.py'
    offset = 0
    limit = 1
    for o, a in opts:
        if o in ('-c', '--conf'):
            conf = a
        elif o in ('-o', '--offset'):
            offset = int(a)
        elif o in ('-l', '--limit'):
            limit = int(a)
        elif o in ('-h', '--help'):
            usage(); sys.exit()

    if len(args) < 1:
        usage()
    else:
        run(args[0], conf, offset, limit)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = sphinx_client
import sphinxapi
import web

from fsphinx import FSphinxClient, Facet, DBFetch, SplitOnSep
from fsphinx import QueryParser, MultiFieldQuery, RedisCache

# connect to database
db = web.database(dbn='mysql', db='fsphinx', user='fsphinx', passwd='fsphinx')

# let's have a cache for later use
cache = RedisCache(db=0)

# show output of mysql statements
db.printing = False

# create sphinx client
cl = FSphinxClient()

# connect to searchd
cl.SetServer('localhost', 10001)

# matching mode (faceted client should be SPH_MATCH_EXTENDED2)
cl.SetMatchMode(sphinxapi.SPH_MATCH_EXTENDED2)

# sorting and possible custom sorting function
cl.SetSortMode(sphinxapi.SPH_SORT_EXPR, '@weight * user_rating_attr * nb_votes_attr * year_attr / 100000')

# set the default index to search
cl.SetDefaultIndex('items')

# some fields could matter more than others
cl.SetFieldWeights({'title' : 30})

# sql query to fetch the hits
db_fetch = DBFetch(db, sql = '''
select 
    imdb_id as id,
    filename, title, year, user_rating, nb_votes, type_tv_serie, type_other, 
    release_date, release_date_raw, plot, awards, runtime, 
    color, aspect_ratio, certification, 
    cover_url, gallery_url, trailer_url, release_date_raw, 
    (select group_concat(distinct director_name separator '@#@') from directors as d where d.imdb_id = t.imdb_id) as director, 
    (select group_concat(distinct actor_name separator '@#@') from casts as c where c.imdb_id = t.imdb_id) as actor, 
    (select group_concat(distinct genre separator '@#@') from genres as g where g.imdb_id = t.imdb_id) as genre, 
    (select group_concat(distinct plot_keyword separator '@#@') from plot_keywords as p where p.imdb_id = t.imdb_id) as keyword 
from titles as t 
where imdb_id in ($id)
order by field(imdb_id, $id)''', post_processors = [
    SplitOnSep('director', 'actor', 'genre', 'keyword', sep='@#@')
]
)
cl.AttachDBFetch(db_fetch)

# give it a cache for the search and the facets
#cl.AttachCache(cache)

# setup the different facets
cl.AttachFacets(
    Facet('year', sql_table=None),
    Facet('genre'),
    Facet('keyword', attr='plot_keyword_attr', sql_col='plot_keyword', sql_table='plot_keyword_terms'),
    Facet('director'),
    Facet('actor'),
)

# for all facets compute count, groupby and this score
group_func = '''
sum(
    if (runtime_attr > 45,
        if (nb_votes_attr > 1000,
            if (nb_votes_attr < 10000, nb_votes_attr * user_rating_attr, 10000 * user_rating_attr),
        1000 * user_rating_attr),
    300 * user_rating_attr)
)'''

# setup sorting and ordering of each facet 
for f in cl.facets:
    f.SetGroupFunc(group_func)
    # order the term alphabetically within each facet
    f.SetOrderBy('@term')
    
# the query should always be parsed beforehand 
query_parser = QueryParser(MultiFieldQuery, user_sph_map={
    'genre' : 'genres', 
    'keyword' : 'plot_keywords', 
    'director' : 'directors', 
    'actor' : 'actors'
})
cl.AttachQueryParser(query_parser)

########NEW FILE########
__FILENAME__ = test
﻿## Setting up

# importing required modules
import sphinxapi
from fsphinx import *

# let's build a Sphinx Client
cl = sphinxapi.SphinxClient()

# assuming searchd is running on 10001
cl.SetServer('localhost', 10001)

# let's have a handle to our fsphinx database
db = utils.database(dbn='mysql', db='fsphinx', user='fsphinx', passwd='fsphinx')

# let's have a cache for later use
cache = RedisCache(db=0)

## Playing with Facets

# sql_table is optional and defaults to (facet_name)_terms
factor = Facet('actor', sql_table='actor_terms')

# the sphinx client is what will perform the computation
factor.AttachSphinxClient(cl, db)

# let's set the number of facet values returned to 5
factor.SetMaxNumValues(5)

# computing the actor facet for the query "drama"
factor.Compute('drama')

# let's see how this looks like
print factor

# setting up a custom sorting function
factor.SetGroupFunc('sum(user_rating_attr * nb_votes_attr)')

# @groupfunc holds the value of the custom grouping function
factor.SetOrderBy('@groupfunc', order='desc')

# computing the actor facet for the query "drama"
factor.Compute('drama')

# let's what we get
print factor

# sql_table is optional and defaults to (facet_name)_terms
fyear = Facet('year', sql_table=None)

# let's put the facets in a group for faster computation
facets = FacetGroup(fyear, factor)

# as always Sphinx is what carries the computation
facets.AttachSphinxClient(cl, db)

# finally compute these two facets at once
facets.Compute("drama", caching=False)

# turning caching on
facets.AttachCache(cache)

# computing facets twice with caching on
facets.Compute('drama')
facets.Compute('drama')
assert(facets.time == 0)

# this makes sure the facet computation is not fetched from the cache
facets.Compute('drama', caching=False)
assert(facets.time > 0)

## Playing With Multi-field Queries

# creating a multi-field query
query = MultiFieldQuery(user_sph_map={'actor':'actors', 'genre':'genres'})

# parsing a multi-field query
query.Parse('@year 1999 @genre drama @actor harrison ford')

# the query the user will see: '(@year 1999) (@genre drama) (@actor harrison ford)'
print query.user

# the query that should be passed to Sphinx: '(@genres drama) (@actors harrison ford)'
print query.sphinx

# let's toggle the year field off
query['@year 1999'].ToggleOff()

# the query the user will see: '(@-year 1999) (@genre drama) (@actor harrison ford)'
print query.user

# the query that should be sent to sphinx: '(@genres drama) (@actors harrison ford)'
print query.sphinx

# is the query term '@year 1999' in query
assert('@year 1999' in query)

# a connical form of this query: (@actors harrison ford) (@genres drama)
print query.uniq

# a unique url path representing this query: /actor/harrison+ford/genre/drama/year/*1999/?ot=210
print query.ToPrettyUrl()

# setting cl to extended matching mode
cl.SetMatchMode(sphinxapi.SPH_MATCH_EXTENDED2)

# and now passing a multi-field query object
factor.Compute(query)

# and looking at the results
print factor

## Retrieving Results

# let's fetch the results from the DB
db_fetch = DBFetch(db, sql = 
'''select 
    imdb_id, filename, title, year, plot,    
    (select group_concat(distinct director_name separator '@#@') from directors as d 
    where d.imdb_id = t.imdb_id) as directors
    from titles as t 
    where imdb_id in ($id)
    order by field(imdb_id, $id)
''')

# let's perform a simple query
results = cl.Query('movie')

# and fetch the results form the DB
hits = db_fetch.Fetch(results)

# looking at the hits
print hits

## Full text search is fine, how about item based search?

# make sure you have SimSearch installed
import simsearch

# assuming we have created a similarity search index
index = simsearch.ComputedIndex('./data/sim-index/')

# and a query handler to query it
handler = simsearch.QueryHandler(index)

# and wrap cl to give it similarity search abilities
cl = simsearch.SimClient(cl, handler)

# order by similarity search scores
cl.SetSortMode(sphinxapi.SPH_SORT_EXPR, 'log_score_attr')      

# looking for movies similar to Terminator (movie id = 88247)
cl.Query('@similar 88247')

## Putting Everything Together

# creating a sphinx client
cl = FSphinxClient()

# it behaves exactly like a normal SphinxClient
cl.SetServer('localhost', 10001)

# get the results from the db
cl.AttachDBFetch(db_fetch)

# attach the facets
cl.AttachFacets(fyear, factor)

# running the query
cl.Query('movie')

# or pass a MultiFieldQuery
cl.Query(query)
    
## Playing With Configuration Files

cl = FSphinxClient.FromConfig('./config/sphinx_client.py')

# querying for "movie"
hits = cl.Query('movie')

print hits
########NEW FILE########
