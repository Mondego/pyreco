__FILENAME__ = changes
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

"""
module to fetch and stream changes from a database
"""

from .utils import json


class ChangesStream(object):
    """\
    Change stream object.

    .. code-block:: python

        from couchdbkit import Server from couchdbkit.changes import ChangesStream

        s = Server()
        db = s['testdb']
        stream = ChangesStream(db)

        print "got change now"
        for c in stream:
            print c

        print "stream changes"
        with ChangesStream(db, feed="continuous",  heartbeat=True) as stream:
            for c in stream: print c

    """

    def __init__(self, db, **params):
        self.db = db
        self.params = params

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __iter__(self):
        r = self.db.res.get("_changes", **self.params)
        with r.body_stream() as body:
            while True:
                line = body.readline()
                if not line:
                    break
                if line.endswith("\r\n"):
                    line = line[:-2]
                else:
                    line = line[:-1]
                if not line:
                    #heartbeat
                    continue

                if line.endswith(","):
                    line = line[:-1]
                ret = self._parse_change(line)
                if not ret:
                    continue
                yield ret

    def _parse_change(self, line):
        if line.startswith('{"results":') or line.startswith('"last_seq'):
            return None
        else:
            try:
                obj = json.loads(line)
                return obj
            except ValueError:
                return None

    def __next__(self):
        return self


def fold(db, fun, acc, since=0):
    """Fold each changes and accuumulate result using a function

    Args:

        @param db: Database, a database object
        @param fun: function, a callable with arity 2
        @param since: int, sequence where to start the feed

    @return: list, last acc returned

    Ex of function:

        fun(change_object,acc):
            return acc

    If the function return "stop", the changes feed will stop.


    """

    if not callable(fun):
        raise TypeError("fun isn't a callable")

    with ChangesStream(db, since=since) as st:
        for c in st:
            acc = fun(c, acc)
    return acc


def foreach(db, fun, since=0):
    """Iter each changes and pass it to the callable"""

    if not callable(fun):
        raise TypeError("fun isn't a callable")

    with ChangesStream(db, since=since) as st:
        for c in st:
            fun(c)

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

"""
Client implementation for CouchDB access. It allows you to manage a CouchDB
server, databases, documents and views. All objects mostly reflect python
objects for convenience. Server and Database objects for example, can be
used as easy as a dict.

Example:

    >>> from couchdbkit import Server
    >>> server = Server()
    >>> db = server.create_db('couchdbkit_test')
    >>> doc = { 'string': 'test', 'number': 4 }
    >>> db.save_doc(doc)
    >>> docid = doc['_id']
    >>> doc2 = db.get(docid)
    >>> doc['string']
    u'test'
    >>> del db[docid]
    >>> docid in db
    False
    >>> del server['simplecouchdb_test']

"""

UNKOWN_INFO = {}


from collections import deque
from itertools import groupby
from mimetypes import guess_type
import time

from restkit.util import url_quote

from .exceptions import InvalidAttachment, NoResultFound, \
ResourceNotFound, ResourceConflict, BulkSaveError, MultipleResultsFound
from . import resource
from .utils import validate_dbname

from .schema.util import maybe_schema_wrapper


DEFAULT_UUID_BATCH_COUNT = 1000

def _maybe_serialize(doc):
    if hasattr(doc, "to_json"):
        # try to validate doc first
        try:
            doc.validate()
        except AttributeError:
            pass

        return doc.to_json(), True
    elif isinstance(doc, dict):
        return doc.copy(), False

    return doc, False

class Server(object):
    """ Server object that allows you to access and manage a couchdb node.
    A Server object can be used like any `dict` object.
    """

    resource_class = resource.CouchdbResource

    def __init__(self, uri='http://127.0.0.1:5984',
            uuid_batch_count=DEFAULT_UUID_BATCH_COUNT,
            resource_class=None, resource_instance=None,
            **client_opts):

        """ constructor for Server object

        @param uri: uri of CouchDb host
        @param uuid_batch_count: max of uuids to get in one time
        @param resource_instance: `restkit.resource.CouchdbDBResource` instance.
            It alows you to set a resource class with custom parameters.
        """

        if not uri or uri is None:
            raise ValueError("Server uri is missing")

        if uri.endswith("/"):
            uri = uri[:-1]

        self.uri = uri
        self.uuid_batch_count = uuid_batch_count
        self._uuid_batch_count = uuid_batch_count

        if resource_class is not None:
            self.resource_class = resource_class

        if resource_instance and isinstance(resource_instance,
                                resource.CouchdbResource):
            resource_instance.initial['uri'] = uri
            self.res = resource_instance.clone()
            if client_opts:
                self.res.client_opts.update(client_opts)
        else:
            self.res = self.resource_class(uri, **client_opts)
        self._uuids = deque()

    def info(self):
        """ info of server

        @return: dict

        """
        try:
            resp = self.res.get()
        except Exception:
            return UNKOWN_INFO

        return resp.json_body

    def all_dbs(self):
        """ get list of databases in CouchDb host

        """
        return self.res.get('/_all_dbs').json_body

    def get_db(self, dbname, **params):
        """
        Try to return a Database object for dbname.

        """
        return Database(self._db_uri(dbname), server=self, **params)

    def create_db(self, dbname, **params):
        """ Create a database on CouchDb host

        @param dname: str, name of db
        @param param: custom parameters to pass to create a db. For
        example if you use couchdbkit to access to cloudant or bigcouch:

            Ex: q=12 or n=4

        See https://github.com/cloudant/bigcouch for more info.

        @return: Database instance if it's ok or dict message
        """
        return self.get_db(dbname, create=True, **params)

    get_or_create_db = create_db
    get_or_create_db.__doc__ = """
        Try to return a Database object for dbname. If
        database doest't exist, it will be created.

        """

    def delete_db(self, dbname):
        """
        Delete database
        """
        del self[dbname]

    #TODO: maintain list of replications
    def replicate(self, source, target, **params):
        """
        simple handler for replication

        @param source: str, URI or dbname of the source
        @param target: str, URI or dbname of the target
        @param params: replication options

        More info about replication here :
        http://wiki.apache.org/couchdb/Replication

        """
        payload = {
            "source": source,
            "target": target,
        }
        payload.update(params)
        resp = self.res.post('/_replicate', payload=payload)
        return resp.json_body

    def active_tasks(self):
        """ return active tasks """
        resp = self.res.get('/_active_tasks')
        return resp.json_body

    def uuids(self, count=1):
        return self.res.get('/_uuids', count=count).json_body

    def next_uuid(self, count=None):
        """
        return an available uuid from couchdbkit
        """
        if count is not None:
            self._uuid_batch_count = count
        else:
            self._uuid_batch_count = self.uuid_batch_count

        try:
            return self._uuids.pop()
        except IndexError:
            self._uuids.extend(self.uuids(count=self._uuid_batch_count)["uuids"])
            return self._uuids.pop()

    def __getitem__(self, dbname):
        return Database(self._db_uri(dbname), server=self)

    def __delitem__(self, dbname):
        ret = self.res.delete('/%s/' % url_quote(dbname,
            safe=":")).json_body
        return ret

    def __contains__(self, dbname):
        try:
            self.res.head('/%s/' % url_quote(dbname, safe=":"))
        except:
            return False
        return True

    def __iter__(self):
        for dbname in self.all_dbs():
            yield Database(self._db_uri(dbname), server=self)

    def __len__(self):
        return len(self.all_dbs())

    def __nonzero__(self):
        return (len(self) > 0)

    def _db_uri(self, dbname):
        if dbname.startswith("/"):
            dbname = dbname[1:]

        dbname = url_quote(dbname, safe=":")
        return "/".join([self.uri, dbname])

class Database(object):
    """ Object that abstract access to a CouchDB database
    A Database object can act as a Dict object.
    """

    def __init__(self, uri, create=False, server=None, **params):
        """Constructor for Database

        @param uri: str, Database uri
        @param create: boolean, False by default,
        if True try to create the database.
        @param server: Server instance

        """
        self.uri = uri.rstrip('/')
        self.server_uri, self.dbname = self.uri.rsplit("/", 1)

        if server is not None:
            if not hasattr(server, 'next_uuid'):
                raise TypeError('%s is not a couchdbkit.Server instance' %
                            server.__class__.__name__)
            self.server = server
        else:
            self.server = server = Server(self.server_uri, **params)

        validate_dbname(self.dbname)
        if create:
            try:
                self.server.res.head('/%s/' % self.dbname)
            except ResourceNotFound:
                self.server.res.put('/%s/' % self.dbname, **params).json_body

        self.res = server.res(self.dbname)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.dbname)

    def info(self):
        """
        Get database information

        @return: dict
        """
        return self.res.get().json_body

    def set_security(self, secobj):
        """ set database securrity object """
        return self.res.put("/_security", payload=secobj).json_body

    def get_security(self):
        """ get database secuirity object """
        return self.res.get("/_security").json_body

    def compact(self, dname=None):
        """ compact database
        @param dname: string, name of design doc. Usefull to
        compact a view.
        """
        path = "/_compact"
        if dname is not None:
            path = "%s/%s" % (path, resource.escape_docid(dname))
        res = self.res.post(path, headers={"Content-Type":
            "application/json"})
        return res.json_body

    def view_cleanup(self):
        res = self.res.post('/_view_cleanup', headers={"Content-Type":
            "application/json"})
        return res.json_body

    def flush(self):
        """ Remove all docs from a database
        except design docs."""

        # save ddocs
        all_ddocs = self.all_docs(startkey="_design",
                            endkey="_design/"+u"\u9999",
                            include_docs=True)
        ddocs = []
        for ddoc in all_ddocs:
            doc = ddoc['doc']
            old_atts = doc.get('_attachments', {})
            atts = {}
            for name, info in old_atts.items():
                att = {}
                att['content_type'] = info['content_type']
                att['data'] = self.fetch_attachment(ddoc['doc'], name)
                atts[name] = att

            # create a fresh doc
            doc.pop('_rev')
            doc['_attachments'] = resource.encode_attachments(atts)

            ddocs.append(doc)

        # delete db
        self.server.delete_db(self.dbname)

        # we let a chance to the system to sync
        times = 0
        while times < 10:
            try:
                self.server.res.head('/%s/' % self.dbname)
            except ResourceNotFound:
                break
            time.sleep(0.2)
            times += 1

        # recreate db + ddocs
        self.server.create_db(self.dbname)
        self.bulk_save(ddocs)

    def doc_exist(self, docid):
        """Test if document exists in a database

        @param docid: str, document id
        @return: boolean, True if document exist
        """

        try:
            self.res.head(resource.escape_docid(docid))
        except ResourceNotFound:
            return False
        return True

    def open_doc(self, docid, **params):
        """Get document from database

        Args:
        @param docid: str, document id to retrieve
        @param wrapper: callable. function that takes dict as a param.
        Used to wrap an object.
        @param **params: See doc api for parameters to use:
        http://wiki.apache.org/couchdb/HTTP_Document_API

        @return: dict, representation of CouchDB document as
         a dict.
        """
        wrapper = None
        if "wrapper" in params:
            wrapper = params.pop("wrapper")
        elif "schema" in params:
            schema = params.pop("schema")
            if not hasattr(schema, "wrap"):
                raise TypeError("invalid schema")
            wrapper = schema.wrap

        docid = resource.escape_docid(docid)
        doc = self.res.get(docid, **params).json_body
        if wrapper is not None:
            if not callable(wrapper):
                raise TypeError("wrapper isn't a callable")

            return wrapper(doc)

        return doc
    get = open_doc

    def list(self, list_name, view_name, **params):
        """ Execute a list function on the server and return the response.
        If the response is json it will be deserialized, otherwise the string
        will be returned.

        Args:
            @param list_name: should be 'designname/listname'
            @param view_name: name of the view to run through the list document
            @param params: params of the list
        """
        list_name = list_name.split('/')
        dname = list_name.pop(0)
        vname = '/'.join(list_name)
        list_path = '_design/%s/_list/%s/%s' % (dname, vname, view_name)

        return self.res.get(list_path, **params).json_body

    def show(self, show_name, doc_id, **params):
        """ Execute a show function on the server and return the response.
        If the response is json it will be deserialized, otherwise the string
        will be returned.

        Args:
            @param show_name: should be 'designname/showname'
            @param doc_id: id of the document to pass into the show document
            @param params: params of the show
        """
        show_name = show_name.split('/')
        dname = show_name.pop(0)
        vname = '/'.join(show_name)
        show_path = '_design/%s/_show/%s/%s' % (dname, vname, doc_id)

        return self.res.get(show_path, **params).json_body

    def update(self, update_name, doc_id=None, **params):
        """ Execute update function on the server and return the response.
        If the response is json it will be deserialized, otherwise the string
        will be returned.

        Args:
            @param update_name: should be 'designname/updatename'
            @param doc_id: id of the document to pass into the update function
            @param params: params of the update
        """
        update_name = update_name.split('/')
        dname = update_name.pop(0)
        uname = '/'.join(update_name)

        if doc_id is None:
            update_path = '_design/%s/_update/%s' % (dname, uname)
            return self.res.post(update_path, **params).json_body
        else:
            update_path = '_design/%s/_update/%s/%s' % (dname, uname, doc_id)
            return self.res.put(update_path, **params).json_body

    def all_docs(self, by_seq=False, **params):
        """Get all documents from a database

        This method has the same behavior as a view.

        `all_docs( **params )` is the same as `view('_all_docs', **params)`
         and `all_docs( by_seq=True, **params)` is the same as
        `view('_all_docs_by_seq', **params)`

        You can use all(), one(), first() just like views

        Args:
        @param by_seq: bool, if True the "_all_docs_by_seq" is passed to
        couchdb. It will return an updated list of all documents.

        @return: list, results of the view
        """
        if by_seq:
            try:
                return self.view('_all_docs_by_seq', **params)
            except ResourceNotFound:
                # CouchDB 0.11 or sup
                raise AttributeError("_all_docs_by_seq isn't supported on Couchdb %s" % self.server.info()[1])

        return self.view('_all_docs', **params)

    def get_rev(self, docid):
        """ Get last revision from docid (the '_rev' member)
        @param docid: str, undecoded document id.

        @return rev: str, the last revision of document.
        """
        response = self.res.head(resource.escape_docid(docid))
        return response['etag'].strip('"')

    def save_doc(self, doc, encode_attachments=True, force_update=False,
            **params):
        """ Save a document. It will use the `_id` member of the document
        or request a new uuid from CouchDB. IDs are attached to
        documents on the client side because POST has the curious property of
        being automatically retried by proxies in the event of network
        segmentation and lost responses. (Idee from `Couchrest <http://github.com/jchris/couchrest/>`)

        @param doc: dict.  doc is updated
        with doc '_id' and '_rev' properties returned
        by CouchDB server when you save.
        @param force_update: boolean, if there is conlict, try to update
        with latest revision
        @param params, list of optionnal params, like batch="ok"

        @return res: result of save. doc is updated in the mean time
        """
        if doc is None:
            doc1 = {}
        else:
            doc1, schema = _maybe_serialize(doc)

        if '_attachments' in doc1 and encode_attachments:
            doc1['_attachments'] = resource.encode_attachments(doc['_attachments'])

        if '_id' in doc:
            docid = doc1['_id']
            docid1 = resource.escape_docid(doc1['_id'])
            try:
                res = self.res.put(docid1, payload=doc1,
                        **params).json_body
            except ResourceConflict:
                if force_update:
                    doc1['_rev'] = self.get_rev(docid)
                    res =self.res.put(docid1, payload=doc1,
                            **params).json_body
                else:
                    raise
        else:
            try:
                doc['_id'] = self.server.next_uuid()
                res =  self.res.put(doc['_id'], payload=doc1,
                        **params).json_body
            except:
                res = self.res.post(payload=doc1, **params).json_body

        if 'batch' in params and 'id' in res:
            doc1.update({ '_id': res['id']})
        else:
            doc1.update({'_id': res['id'], '_rev': res['rev']})


        if schema:
            doc._doc = doc1
        else:
            doc.update(doc1)
        return res

    def save_docs(self, docs, use_uuids=True, all_or_nothing=False, new_edits=None,
            **params):
        """ bulk save. Modify Multiple Documents With a Single Request

        @param docs: list of docs
        @param use_uuids: add _id in doc who don't have it already set.
        @param all_or_nothing: In the case of a power failure, when the database
        restarts either all the changes will have been saved or none of them.
        However, it does not do conflict checking, so the documents will
        @param new_edits: When False, this saves existing revisions instead of
        creating new ones. Used in the replication Algorithm. Each document
        should have a _revisions property that lists its revision history.

        .. seealso:: `HTTP Bulk Document API <http://wiki.apache.org/couchdb/HTTP_Bulk_Document_API>`

        """

        docs1 = []
        docs_schema = []
        for doc in docs:
            doc1, schema = _maybe_serialize(doc)
            docs1.append(doc1)
            docs_schema.append(schema)

        def is_id(doc):
            return '_id' in doc

        if use_uuids:
            noids = []
            for k, g in groupby(docs1, is_id):
                if not k:
                    noids = list(g)

            uuid_count = max(len(noids), self.server.uuid_batch_count)
            for doc in noids:
                nextid = self.server.next_uuid(count=uuid_count)
                if nextid:
                    doc['_id'] = nextid

        payload = { "docs": docs1 }
        if all_or_nothing:
            payload["all_or_nothing"] = True
        if new_edits is not None:
            payload["new_edits"] = new_edits

        # update docs
        results = self.res.post('/_bulk_docs',
                payload=payload, **params).json_body

        errors = []
        for i, res in enumerate(results):
            if 'error' in res:
                errors.append(res)
            else:
                if docs_schema[i]:
                    docs[i]._doc.update({
                        '_id': res['id'],
                        '_rev': res['rev']
                    })
                else:
                    docs[i].update({
                        '_id': res['id'],
                        '_rev': res['rev']
                    })
        if errors:
            raise BulkSaveError(errors, results)
        return results
    bulk_save = save_docs

    def delete_docs(self, docs, all_or_nothing=False,
            empty_on_delete=False, **params):
        """ bulk delete.
        It adds '_deleted' member to doc then uses bulk_save to save them.

        @param empty_on_delete: default is False if you want to make
        sure the doc is emptied and will not be stored as is in Apache
        CouchDB.
        @param all_or_nothing: In the case of a power failure, when the database
        restarts either all the changes will have been saved or none of them.
        However, it does not do conflict checking, so the documents will

        .. seealso:: `HTTP Bulk Document API <http://wiki.apache.org/couchdb/HTTP_Bulk_Document_API>`


        """

        if empty_on_delete:
            for doc in docs:
                new_doc = {"_id": doc["_id"],
                        "_rev": doc["_rev"],
                        "_deleted": True}
                doc.clear()
                doc.update(new_doc)
        else:
            for doc in docs:
                doc['_deleted'] = True

        return self.bulk_save(docs, use_uuids=False,
                all_or_nothing=all_or_nothing, **params)

    bulk_delete = delete_docs

    def delete_doc(self, doc, **params):
        """ delete a document or a list of documents
        @param doc: str or dict,  document id or full doc.
        @return: dict like:

        .. code-block:: python

            {"ok":true,"rev":"2839830636"}
        """
        result = { 'ok': False }

        doc1, schema = _maybe_serialize(doc)
        if isinstance(doc1, dict):
            if not '_id' or not '_rev' in doc1:
                raise KeyError('_id and _rev are required to delete a doc')

            docid = resource.escape_docid(doc1['_id'])
            result = self.res.delete(docid, rev=doc1['_rev'], **params).json_body
        elif isinstance(doc1, basestring): # we get a docid
            rev = self.get_rev(doc1)
            docid = resource.escape_docid(doc1)
            result = self.res.delete(docid, rev=rev, **params).json_body

        if schema:
            doc._doc.update({
                "_rev": result['rev'],
                "_deleted": True
            })
        elif isinstance(doc, dict):
            doc.update({
                "_rev": result['rev'],
                "_deleted": True
            })
        return result

    def copy_doc(self, doc, dest=None, headers=None):
        """ copy an existing document to a new id. If dest is None, a new uuid will be requested
        @param doc: dict or string, document or document id
        @param dest: basestring or dict. if _rev is specified in dict it will override the doc
        """

        if not headers:
            headers = {}

        doc1, schema = _maybe_serialize(doc)
        if isinstance(doc1, basestring):
            docid = doc1
        else:
            if not '_id' in doc1:
                raise KeyError('_id is required to copy a doc')
            docid = doc1['_id']

        if dest is None:
            destination = self.server.next_uuid(count=1)
        elif isinstance(dest, basestring):
            if dest in self:
                dest = self.get(dest)
                destination = "%s?rev=%s" % (dest['_id'], dest['_rev'])
            else:
                destination = dest
        elif isinstance(dest, dict):
            if '_id' in dest and '_rev' in dest and dest['_id'] in self:
                destination = "%s?rev=%s" % (dest['_id'], dest['_rev'])
            else:
                raise KeyError("dest doesn't exist or this not a document ('_id' or '_rev' missig).")

        if destination:
            headers.update({"Destination": str(destination)})
            result = self.res.copy('/%s' % docid, headers=headers).json_body
            return result

        return { 'ok': False }

    def raw_view(self, view_path, params):
        if 'keys' in params:
            keys = params.pop('keys')
            return self.res.post(view_path, payload={ 'keys': keys }, **params)
        else:
            return self.res.get(view_path, **params)

    def raw_temp_view(db, design, params):
        return db.res.post('_temp_view', payload=design,
               headers={"Content-Type": "application/json"}, **params)

    def view(self, view_name, schema=None, wrapper=None, **params):
        """ get view results from database. viewname is generally
        a string like `designname/viewname". It return an ViewResults
        object on which you could iterate, list, ... . You could wrap
        results in wrapper function, a wrapper function take a row
        as argument. Wrapping could be also done by passing an Object
        in obj arguments. This Object should have a `wrap` method
        that work like a simple wrapper function.

        @param view_name, string could be '_all_docs', '_all_docs_by_seq',
        'designname/viewname' if view_name start with a "/" it won't be parsed
        and beginning slash will be removed. Usefull with c-l for example.
        @param schema, Object with a wrapper function
        @param wrapper: function used to wrap results
        @param params: params of the view

        """

        if view_name.startswith('/'):
            view_name = view_name[1:]
        if view_name == '_all_docs':
            view_path = view_name
        elif view_name == '_all_docs_by_seq':
            view_path = view_name
        else:
            view_name = view_name.split('/')
            dname = view_name.pop(0)
            vname = '/'.join(view_name)
            view_path = '_design/%s/_view/%s' % (dname, vname)

        return ViewResults(self.raw_view, view_path, wrapper, schema, params)

    def temp_view(self, design, schema=None, wrapper=None, **params):
        """ get adhoc view results. Like view it reeturn a ViewResult object."""
        return ViewResults(self.raw_temp_view, design, wrapper, schema, params)

    def search( self, view_name, handler='_fti/_design', wrapper=None, schema=None, **params):
        """ Search. Return results from search. Use couchdb-lucene
        with its default settings by default."""
        return ViewResults(self.raw_view,
                    "/%s/%s" % (handler, view_name),
                    wrapper=wrapper, schema=schema, params=params)

    def documents(self, schema=None, wrapper=None, **params):
        """ return a ViewResults objects containing all documents.
        This is a shorthand to view function.
        """
        return ViewResults(self.raw_view, '_all_docs',
                wrapper=wrapper, schema=schema, params=params)
    iterdocuments = documents



    def put_attachment(self, doc, content, name=None, content_type=None,
            content_length=None, headers=None):
        """ Add attachement to a document. All attachments are streamed.

        @param doc: dict, document object
        @param content: string or :obj:`File` object.
        @param name: name or attachment (file name).
        @param content_type: string, mimetype of attachment.
        If you don't set it, it will be autodetected.
        @param content_lenght: int, size of attachment.

        @return: bool, True if everything was ok.


        Example:

            >>> from simplecouchdb import server
            >>> server = server()
            >>> db = server.create_db('couchdbkit_test')
            >>> doc = { 'string': 'test', 'number': 4 }
            >>> db.save(doc)
            >>> text_attachment = u'un texte attaché'
            >>> db.put_attachment(doc, text_attachment, "test", "text/plain")
            True
            >>> file = db.fetch_attachment(doc, 'test')
            >>> result = db.delete_attachment(doc, 'test')
            >>> result['ok']
            True
            >>> db.fetch_attachment(doc, 'test')
            >>> del server['couchdbkit_test']
            {u'ok': True}
        """

        if not headers:
            headers = {}

        if not content:
            content = ""
            content_length = 0
        if name is None:
            if hasattr(content, "name"):
                name = content.name
            else:
                raise InvalidAttachment('You should provide a valid attachment name')
        name = url_quote(name, safe="")
        if content_type is None:
            content_type = ';'.join(filter(None, guess_type(name)))

        if content_type:
            headers['Content-Type'] = content_type

        # add appropriate headers
        if content_length and content_length is not None:
            headers['Content-Length'] = content_length

        doc1, schema = _maybe_serialize(doc)

        docid = resource.escape_docid(doc1['_id'])
        res = self.res(docid).put(name, payload=content,
                headers=headers, rev=doc1['_rev']).json_body

        if res['ok']:
            new_doc = self.get(doc1['_id'], rev=res['rev'])
            doc.update(new_doc)
        return res['ok']

    def delete_attachment(self, doc, name, headers=None):
        """ delete attachement to the document

        @param doc: dict, document object in python
        @param name: name of attachement

        @return: dict, with member ok set to True if delete was ok.
        """
        doc1, schema = _maybe_serialize(doc)

        docid = resource.escape_docid(doc1['_id'])
        name = url_quote(name, safe="")

        res = self.res(docid).delete(name, rev=doc1['_rev'],
                headers=headers).json_body
        if res['ok']:
            new_doc = self.get(doc1['_id'], rev=res['rev'])
            doc.update(new_doc)
        return res['ok']


    def fetch_attachment(self, id_or_doc, name, stream=False,
            headers=None):
        """ get attachment in a document

        @param id_or_doc: str or dict, doc id or document dict
        @param name: name of attachment default: default result
        @param stream: boolean, if True return a file object
        @return: `restkit.httpc.Response` object
        """

        if isinstance(id_or_doc, basestring):
            docid = id_or_doc
        else:
            doc, schema = _maybe_serialize(id_or_doc)
            docid = doc['_id']

        docid = resource.escape_docid(docid)
        name = url_quote(name, safe="")

        resp = self.res(docid).get(name, headers=headers)
        if stream:
            return resp.body_stream()
        return resp.body_string(charset="utf-8")


    def ensure_full_commit(self):
        """ commit all docs in memory """
        return self.res.post('_ensure_full_commit', headers={
            "Content-Type": "application/json"
        }).json_body

    def __len__(self):
        return self.info()['doc_count']

    def __contains__(self, docid):
        return self.doc_exist(docid)

    def __getitem__(self, docid):
        return self.get(docid)

    def __setitem__(self, docid, doc):
        doc['_id'] = docid
        self.save_doc(doc)


    def __delitem__(self, docid):
       self.delete_doc(docid)

    def __iter__(self):
        return self.documents().iterator()

    def __nonzero__(self):
        return (len(self) > 0)

class ViewResults(object):
    """
    Object to retrieve view results.
    """

    def __init__(self, fetch, arg, wrapper, schema, params):
        """
        Constructor of ViewResults object

        @param fetch: function (view_path, params) -> restkit.Response
        @param arg: view path to use when fetching view
        @param wrapper: function to wrap rows with
        @param schema: schema or doc_type -> schema map to wrap rows with
        (only one of wrapper, schema must be set)
        @param params: params to apply when fetching view.

        """
        assert not (wrapper and schema)
        wrap_doc = params.get('wrap_doc', schema is not None)
        if schema:
            schema_wrapper = maybe_schema_wrapper(schema, params)
            def row_wrapper(row):
                data = row.get('value')
                docid = row.get('id')
                doc = row.get('doc')
                if doc is not None and wrap_doc:
                    return schema_wrapper(doc)
                elif not data or data is None:
                    return row
                elif not isinstance(data, dict) or not docid:
                    return row
                else:
                    data['_id'] = docid
                    if 'rev' in data:
                        data['_rev'] = data.pop('rev')
                    return schema_wrapper(data)
        else:
            def row_wrapper(row):
                return row

        self._fetch = fetch
        self._arg = arg
        self.wrapper = wrapper or row_wrapper
        self.params = params or {}
        self._result_cache = None
        self._total_rows = None
        self._offset = 0
        self._dynamic_keys = []

    def iterator(self):
        self._fetch_if_needed()
        rows = self._result_cache.get('rows', [])
        wrapper = self.wrapper
        for row in rows:
            yield wrapper(row)

    def first(self):
        """
        Return the first result of this query or None if the result doesn’t contain any row.

        This results in an execution of the underlying query.
        """

        try:
            return list(self)[0]
        except IndexError:
            return None

    def one(self, except_all=False):
        """
        Return exactly one result or raise an exception.


        Raises `couchdbkit.exceptions.MultipleResultsFound` if multiple rows are returned.
        If except_all is True, raises `couchdbkit.exceptions.NoResultFound`
        if the query selects no rows.

        This results in an execution of the underlying query.
        """

        length = len(self)
        if length > 1:
            raise MultipleResultsFound("%s results found." % length)

        result = self.first()
        if result is None and except_all:
            raise NoResultFound
        return result

    def all(self):
        """ return list of all results """
        return list(self.iterator())

    def count(self):
        """ return number of returned results """
        self._fetch_if_needed()
        return len(self._result_cache.get('rows', []))

    def fetch(self):
        """ fetch results and cache them """
        # reset dynamic keys
        for key in  self._dynamic_keys:
            try:
                delattr(self, key)
            except:
                pass
        self._dynamic_keys = []

        self._result_cache = self.fetch_raw().json_body
        assert isinstance(self._result_cache, dict), 'received an invalid ' \
            'response of type %s: %s' % \
            (type(self._result_cache), repr(self._result_cache))
        self._total_rows = self._result_cache.get('total_rows')
        self._offset = self._result_cache.get('offset', 0)

        # add key in view results that could be added by an external
        # like couchdb-lucene
        for key in self._result_cache.keys():
            if key not in ["total_rows", "offset", "rows"]:
                self._dynamic_keys.append(key)
                setattr(self, key, self._result_cache[key])


    def fetch_raw(self):
        """ retrive the raw result """
        return self._fetch(self._arg, self.params)

    def _fetch_if_needed(self):
        if not self._result_cache:
            self.fetch()

    @property
    def total_rows(self):
        """ return number of total rows in the view """
        self._fetch_if_needed()
        # reduce case, count number of lines
        if self._total_rows is None:
            return self.count()
        return self._total_rows

    @property
    def offset(self):
        """ current position in the view """
        self._fetch_if_needed()
        return self._offset

    def __getitem__(self, key):
        params = self.params.copy()
        if type(key) is slice:
            if key.start is not None:
                params['startkey'] = key.start
            if key.stop is not None:
                params['endkey'] = key.stop
        elif isinstance(key, (list, tuple,)):
            params['keys'] = key
        else:
            params['key'] = key

        return ViewResults(self._fetch, self._arg, wrapper=self.wrapper, params=params, schema=None)

    def __call__(self, **newparams):
        return ViewResults(
            self._fetch, self._arg,
            wrapper=self.wrapper,
            params=dict(self.params, **newparams),
            schema=None,
        )

    def __iter__(self):
        return self.iterator()

    def __len__(self):
        return self.count()

    def __nonzero__(self):
        return bool(len(self))




########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

def check_callable(cb):
    if not callable(cb):
        raise TypeError("callback isn't a callable")

class ConsumerBase(object):

    def __init__(self, db, **kwargs):
        self.db = db

    def fetch(self, cb=None, **params):
        resp = self.db.res.get("_changes", **params)
        if cb is not None:
            check_callable(cb)
            cb(resp.json_body)
        else:
            return resp.json_body

    def wait_once(self, cb=None, **params):
        raise NotImplementedError

    def wait(self, cb, **params):
        raise NotImplementedError
    
    def wait_once_async(self, cb, **params):
        raise NotImplementedError

    def wait_async(self, cb, **params):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = ceventlet
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

import traceback

import eventlet
from eventlet import event

from .base import check_callable
from .sync import SyncConsumer
from ..utils import json


class ChangeConsumer(object):
    def __init__(self, db, callback, **params):
        self.process_change = callback
        self.params = params
        self.db = db
        self.stop_event = event.Event()

    def wait(self):
        eventlet.spawn_n(self._run)
        self.stop_event.wait()

    def wait_async(self):
        eventlet.spawn_n(self._run)

    def _run(self):
        while True:
            try:
                resp = self.db.res.get("_changes", **self.params)
                return self.consume(resp)
            except (SystemExit, KeyboardInterrupt):
                eventlet.sleep(5)
                break
            except:
                traceback.print_exc()
                eventlet.sleep(5)
                break
        self.stop_event.send(True)

    def consume(self, resp):
        raise NotImplementedError

class ContinuousChangeConsumer(ChangeConsumer):

    def consume(self, resp):
        with resp.body_stream() as body:
            while True:
                line = body.readline()
                if not line:
                    break
                if line.endswith("\r\n"):
                    line = line[:-2]
                else:
                    line = line[:-1]
                if not line:
                    continue
                self.process_change(line)
            self.stop_event.send(True)


class LongPollChangeConsumer(ChangeConsumer):

    def consume(self, resp):
        with resp.body_stream() as body:
            buf = []
            while True:
                data = body.read()
                if not data:
                    break
                buf.append(data)
            change = "".join(buf)
            try:
                change = json.loads(change)
            except ValueError:
                pass
            self.process_change(change)
            self.stop_event.send(True)


class EventletConsumer(SyncConsumer):
    def __init__(self, db):
        eventlet.monkey_patch(socket=True)
        super(EventletConsumer, self).__init__(db)

    def _fetch(self, cb, **params):
        resp = self.db.res.get("_changes", **params)
        cb(resp.json_body)

    def fetch(self, cb=None, **params):
        if cb is None:
            return super(EventletConsumer, self).wait_once(**params)
        eventlet.spawn_n(self._fetch, cb, **params)

    def wait_once(self, cb=None, **params):
        if cb is None:
            return super(EventletConsumer, self).wait_once(**params)

        check_callable(cb)
        params.update({"feed": "longpoll"})
        consumer = LongPollChangeConsumer(self.db, callback=cb,
                **params)
        consumer.wait()

    def wait(self, cb, **params):
        params.update({"feed": "continuous"})
        consumer = ContinuousChangeConsumer(self.db, callback=cb,
                **params)
        consumer.wait()

    def wait_once_async(self, cb, **params):
        check_callable(cb)
        params.update({"feed": "longpoll"})
        consumer = LongPollChangeConsumer(self.db, callback=cb,
                **params)
        return consumer.wait_async()

    def wait_async(self, cb, **params):
        check_callable(cb)
        params.update({"feed": "continuous"})
        consumer = ContinuousChangeConsumer(self.db, callback=cb,
                **params)
        return consumer.wait_async()


########NEW FILE########
__FILENAME__ = cgevent
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

import traceback

import gevent
from gevent import event
from gevent import monkey

from .base import check_callable
from .sync import SyncConsumer
from ..utils import json


class ChangeConsumer(object):
    def __init__(self, db, callback, **params):
        self.process_change = callback
        self.params = params
        self.db = db
        self.stop_event = event.Event()

    def stop(self):
        self.stop_event.set()

    def wait(self):
        gevent.spawn(self._run)
        self.stop_event.wait()

    def wait_async(self):
        gevent.spawn(self._run)

    def _run(self):
        while True:
            try:
                resp = self.db.res.get("_changes", **self.params)
                return self.consume(resp)
            except (SystemExit, KeyboardInterrupt):
                gevent.sleep(5)
                break
            except:
                traceback.print_exc()
                gevent.sleep(5)
                break
        self.stop_event.set()

    def consume(self, resp):
        raise NotImplementedError

class ContinuousChangeConsumer(ChangeConsumer):

    def consume(self, resp):
        with resp.body_stream() as body:
            while True:
                line = body.readline()
                if not line:
                    break
                if line.endswith("\r\n"):
                    line = line[:-2]
                else:
                    line = line[:-1]
                if not line:
                    continue
                self.process_change(line)

class LongPollChangeConsumer(ChangeConsumer):

    def consume(self, resp):
        with resp.body_stream() as body:
            buf = []
            while True:
                data = body.read()
                if not data:
                    break
                buf.append(data)
            change = "".join(buf)
            try:
                change = json.loads(change)
            except ValueError:
                pass
            self.process_change(change)


class GeventConsumer(SyncConsumer):
    def __init__(self, db):
        monkey.patch_socket()
        super(GeventConsumer, self).__init__(db)

    def _fetch(self, cb, **params):
        resp = self.db.res.get("_changes", **params)
        cb(resp.json_body)

    def fetch(self, cb=None, **params):
        if cb is None:
            return super(GeventConsumer, self).wait_once(**params)
        return gevent.spawn(self._fetch, cb, **params)

    def wait_once(self, cb=None, **params):
        if cb is None:
            return super(GeventConsumer, self).wait_once(**params)

        check_callable(cb)
        params.update({"feed": "longpoll"})
        consumer = LongPollChangeConsumer(self.db, callback=cb,
                **params)
        consumer.wait()

    def wait(self, cb, **params):
        check_callable(cb)
        params.update({"feed": "continuous"})
        consumer = ContinuousChangeConsumer(self.db, callback=cb,
                **params)
        consumer.wait()

    def wait_once_async(self, cb, **params):
        check_callable(cb)
        params.update({"feed": "longpoll"})
        consumer = LongPollChangeConsumer(self.db, callback=cb,
                **params)
        return consumer.wait_async()

    def wait_async(self, cb, **params):
        check_callable(cb)
        params.update({"feed": "continuous"})
        consumer = ContinuousChangeConsumer(self.db, callback=cb,
                **params)
        return consumer.wait_async()

########NEW FILE########
__FILENAME__ = sync
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

from __future__ import with_statement

from .base import ConsumerBase, check_callable
from ..utils import json

__all__ = ['SyncConsumer']

class SyncConsumer(ConsumerBase):

    def wait_once(self, cb=None, **params):
        if cb is not None:
            check_callable(cb)

        params.update({"feed": "longpoll"})
        resp = self.db.res.get("_changes", **params)
        buf = ""
        with resp.body_stream() as body:
            while True:
                data = body.read()
                if not data:
                    break
                buf += data

            ret = json.loads(buf)
            if cb is not None:
                cb(ret)
                return

            return ret

    def wait(self, cb, **params):
        check_callable(cb)
        params.update({"feed": "continuous"})
        resp = self.db.res.get("_changes", **params)

        with resp.body_stream() as body:
            while True:
                try:
                    line = body.readline()
                    if not line:
                        break
                    if line.endswith("\r\n"):
                        line = line[:-2]
                    else:
                        line = line[:-1]
                    if not line:
                        continue

                    cb(json.loads(line))
                except (KeyboardInterrupt, SystemExit,):
                    break

########NEW FILE########
__FILENAME__ = fs
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

from __future__ import with_statement
import base64
import copy
from hashlib import md5
import logging
import mimetypes
import os
import os.path
import re

from .. import client
from ..exceptions import ResourceNotFound, DesignerError, \
BulkSaveError
from .macros import package_shows, package_views
from .. import utils

if os.name == 'nt':
    def _replace_backslash(name):
        return name.replace("\\", "/")

    def _replace_slash(name):
        return name.replace("/", "\\")
else:
    def _replace_backslash(name):
        return name

    def _replace_slash(name):
        return name

logger = logging.getLogger(__name__)

class FSDoc(object):

    def __init__(self, path, create=False, docid=None, is_ddoc=True):
        self.docdir = path
        self.ignores = []
        self.is_ddoc = is_ddoc

        ignorefile = os.path.join(path, '.couchappignore')
        if os.path.exists(ignorefile):
            # A .couchappignore file is a json file containing a
            # list of regexps for things to skip
            self.ignores = utils.json.load(open(ignorefile, 'r'))
        if not docid:
            docid = self.get_id()
        self.docid = docid
        self._doc = {'_id': self.docid}
        if create:
            self.create()

    def get_id(self):
        """
        if there is an _id file, docid is extracted from it,
        else we take the current folder name.
        """
        idfile = os.path.join(self.docdir, '_id')
        if os.path.exists(idfile):
            docid = utils.read_file(idfile).split("\n")[0].strip()
            if docid: return docid
        if self.is_ddoc:
            return "_design/%s" % os.path.split(self.docdir)[1]
        else:
            return os.path.split(self.docdir)[1]

    def __repr__(self):
        return "<%s (%s/%s)>" % (self.__class__.__name__, self.docdir, self.docid)

    def __str__(self):
        return utils.json.dumps(self.doc())

    def create(self):
        if not os.path.isdir(self.docdir):
            logger.error("%s directory doesn't exist." % self.docdir)

        rcfile = os.path.join(self.docdir, '.couchapprc')
        if not os.path.isfile(rcfile):
            utils.write_json(rcfile, {})
        else:
            logger.warning("CouchApp already initialized in %s." % self.docdir)

    def push(self, dbs, atomic=True, force=False):
        """Push a doc to a list of database `dburls`. If noatomic is true
        each attachments will be sent one by one."""
        for db in dbs:
            if atomic:
                doc = self.doc(db, force=force)
                db.save_doc(doc, force_update=True)
            else:
                doc = self.doc(db, with_attachments=False, force=force)
                db.save_doc(doc, force_update=True)

                attachments = doc.get('_attachments') or {}

                for name, filepath in self.attachments():
                    if name not in attachments:
                        logger.debug("attach %s " % name)
                        db.put_attachment(doc, open(filepath, "r"),
                                            name=name)

            logger.debug("%s/%s had been pushed from %s" % (db.uri,
                self.docid, self.docdir))


    def attachment_stub(self, name, filepath):
        att = {}
        with open(filepath, "rb") as f:
            re_sp = re.compile('\s')
            att = {
                    "data": re_sp.sub('',base64.b64encode(f.read())),
                    "content_type": ';'.join(filter(None,
                                            mimetypes.guess_type(name)))
            }

        return att

    def doc(self, db=None, with_attachments=True, force=False):
        """ Function to reetrieve document object from
        document directory. If `with_attachments` is True
        attachments will be included and encoded"""

        manifest = []
        objects = {}
        signatures = {}
        attachments = {}

        self._doc = {'_id': self.docid}

        # get designdoc
        self._doc.update(self.dir_to_fields(self.docdir, manifest=manifest))

        if not 'couchapp' in self._doc:
            self._doc['couchapp'] = {}

        self.olddoc = {}
        if db is not None:
            try:
                self.olddoc = db.open_doc(self._doc['_id'])
                attachments = self.olddoc.get('_attachments') or {}
                self._doc.update({'_rev': self.olddoc['_rev']})
            except ResourceNotFound:
                self.olddoc = {}

        if 'couchapp' in self.olddoc:
            old_signatures = self.olddoc['couchapp'].get('signatures',
                                                        {})
        else:
            old_signatures = {}

        for name, filepath in self.attachments():
            signatures[name] = utils.sign_file(filepath)
            if with_attachments and not old_signatures:
                logger.debug("attach %s " % name)
                attachments[name] = self.attachment_stub(name, filepath)

        if old_signatures:
            for name, signature in old_signatures.items():
                cursign = signatures.get(name)
                if not cursign:
                    logger.debug("detach %s " % name)
                    del attachments[name]
                elif cursign != signature:
                    logger.debug("detach %s " % name)
                    del attachments[name]
                else:
                    continue

            if with_attachments:
                for name, filepath in self.attachments():
                    if old_signatures.get(name) != signatures.get(name) or force:
                        logger.debug("attach %s " % name)
                        attachments[name] = self.attachment_stub(name, filepath)

        self._doc['_attachments'] = attachments

        self._doc['couchapp'].update({
            'manifest': manifest,
            'objects': objects,
            'signatures': signatures
        })


        if self.docid.startswith('_design/'):  # process macros
            for funs in ['shows', 'lists', 'updates', 'filters',
                    'spatial']:
                if funs in self._doc:
                    package_shows(self._doc, self._doc[funs], self.docdir,
                            objects)

            if 'validate_doc_update' in self._doc:
                tmp_dict = dict(validate_doc_update=self._doc[
                                                    "validate_doc_update"])
                package_shows( self._doc, tmp_dict, self.docdir,
                    objects)
                self._doc.update(tmp_dict)

            if 'views' in  self._doc:
                # clean views
                # we remove empty views and malformed from the list
                # of pushed views. We also clean manifest
                views = {}
                dmanifest = {}
                for i, fname in enumerate(manifest):
                    if fname.startswith("views/") and fname != "views/":
                        name, ext = os.path.splitext(fname)
                        if name.endswith('/'):
                            name = name[:-1]
                        dmanifest[name] = i

                for vname, value in self._doc['views'].iteritems():
                    if value and isinstance(value, dict):
                        views[vname] = value
                    else:
                        del manifest[dmanifest["views/%s" % vname]]
                self._doc['views'] = views
                package_views(self._doc,self._doc["views"], self.docdir,
                        objects)

            if "fulltext" in self._doc:
                package_views(self._doc,self._doc["fulltext"], self.docdir,
                        objects)


        return self._doc

    def check_ignore(self, item):
        for i in self.ignores:
            match = re.match(i, item)
            if match:
                logger.debug("ignoring %s" % item)
                return True
        return False

    def dir_to_fields(self, current_dir='', depth=0,
                manifest=[]):
        """ process a directory and get all members """

        fields={}
        if not current_dir:
            current_dir = self.docdir
        for name in os.listdir(current_dir):
            current_path = os.path.join(current_dir, name)
            rel_path = _replace_backslash(utils.relpath(current_path, self.docdir))
            if name.startswith("."):
                continue
            elif self.check_ignore(name):
                continue
            elif depth == 0 and name.startswith('_'):
                # files starting with "_" are always "special"
                continue
            elif name == '_attachments':
                continue
            elif depth == 0 and (name == 'couchapp' or name == 'couchapp.json'):
                # we are in app_meta
                if name == "couchapp":
                    manifest.append('%s/' % rel_path)
                    content = self.dir_to_fields(current_path,
                        depth=depth+1, manifest=manifest)
                else:
                    manifest.append(rel_path)
                    content = utils.read_json(current_path)
                    if not isinstance(content, dict):
                        content = { "meta": content }
                if 'signatures' in content:
                    del content['signatures']

                if 'manifest' in content:
                    del content['manifest']

                if 'objects' in content:
                    del content['objects']

                if 'length' in content:
                    del content['length']

                if 'couchapp' in fields:
                    fields['couchapp'].update(content)
                else:
                    fields['couchapp'] = content
            elif os.path.isdir(current_path):
                manifest.append('%s/' % rel_path)
                fields[name] = self.dir_to_fields(current_path,
                        depth=depth+1, manifest=manifest)
            else:
                logger.debug("push %s" % rel_path)

                content = ''
                if name.endswith('.json'):
                    try:
                        content = utils.read_json(current_path)
                    except ValueError:
                        logger.error("Json invalid in %s" % current_path)
                else:
                    try:
                        content = utils.read_file(current_path).strip()
                    except UnicodeDecodeError:
                        logger.warning("%s isn't encoded in utf8" % current_path)
                        content = utils.read_file(current_path, utf8=False)
                        try:
                            content.encode('utf-8')
                        except UnicodeError:
                            logger.warning(
                            "plan B didn't work, %s is a binary" % current_path)
                            logger.warning("use plan C: encode to base64")
                            content = "base64-encoded;%s" % base64.b64encode(
                                                                        content)


                # remove extension
                name, ext = os.path.splitext(name)
                if name in fields:
                    logger.warning(
        "%(name)s is already in properties. Can't add (%(fqn)s)" % {
                            "name": name, "fqn": rel_path })
                else:
                    manifest.append(rel_path)
                    fields[name] = content
        return fields

    def _process_attachments(self, path, vendor=None):
        """ the function processing directory to yeld
        attachments. """
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for dirname in dirs:
                    if dirname.startswith('.'):
                        dirs.remove(dirname)
                    elif self.check_ignore(dirname):
                        dirs.remove(dirname)
                if files:
                    for filename in files:
                        if filename.startswith('.'):
                            continue
                        elif self.check_ignore(filename):
                            continue
                        else:
                            filepath = os.path.join(root, filename)
                            name = utils.relpath(filepath, path)
                            if vendor is not None:
                                name = os.path.join('vendor', vendor, name)
                            name = _replace_backslash(name)
                            yield (name, filepath)

    def attachments(self):
        """ This function yield a tuple (name, filepath) corresponding
        to each attachment (vendor included) in the couchapp. `name`
        is the name of attachment in `_attachments` member and `filepath`
        the path to the attachment on the disk.

        attachments are processed later to allow us to send attachments inline
        or one by one.
        """
        # process main attachments
        attachdir = os.path.join(self.docdir, "_attachments")
        for attachment in self._process_attachments(attachdir):
            yield attachment
        vendordir = os.path.join(self.docdir, 'vendor')
        if not os.path.isdir(vendordir):
            logger.debug("%s don't exist" % vendordir)
            return

        for name in os.listdir(vendordir):
            current_path = os.path.join(vendordir, name)
            if os.path.isdir(current_path):
                attachdir = os.path.join(current_path, '_attachments')
                if os.path.isdir(attachdir):
                    for attachment in self._process_attachments(attachdir,
                                                        vendor=name):
                        yield attachment

    def index(self, dburl, index):
        if index is not None:
            return "%s/%s/%s" % (dburl, self.docid, index)
        elif os.path.isfile(os.path.join(self.docdir, "_attachments",
                    'index.html')):
            return "%s/%s/index.html" % (dburl, self.docid)
        return False

def document(path, create=False, docid=None, is_ddoc=True):
    """ simple function to retrive a doc object from filesystem """
    return FSDoc(path, create=create, docid=docid, is_ddoc=is_ddoc)

def push(path, dbs, atomic=True, force=False, docid=None):
    """ push a document from the fs to one or more dbs. Identic to
    couchapp push command """
    if not isinstance(dbs, (list, tuple)):
        dbs = [dbs]

    doc = document(path, create=False, docid=docid)
    doc.push(dbs, atomic=atomic, force=force)
    docspath = os.path.join(path, '_docs')
    if os.path.exists(docspath):
        pushdocs(docspath, dbs, atomic=atomic)

def pushapps(path, dbs, atomic=True, export=False, couchapprc=False):
    """ push all couchapps in one folder like couchapp pushapps command
    line """
    if not isinstance(dbs, (list, tuple)):
        dbs = [dbs]

    apps = []
    for d in os.listdir(path):
        appdir = os.path.join(path, d)
        if os.path.isdir(appdir):
            if couchapprc and not os.path.isfile(os.path.join(appdir,
                '.couchapprc')):
                continue
            doc = document(appdir)
            if not atomic:
                doc.push(dbs, atomic=False)
            else:
                apps.append(doc)
    if apps:
        if export:
            docs= [doc.doc() for doc in apps]
            jsonobj = {'docs': docs}
            return jsonobj
        else:
            for db in dbs:
                docs = []
                docs = [doc.doc(db) for doc in apps]
                try:
                    db.save_docs(docs)
                except BulkSaveError, e:
                    docs1 = []
                    for doc in e.errors:
                        try:
                            doc['_rev'] = db.get_rev(doc['_id'])
                            docs1.append(doc)
                        except ResourceNotFound:
                            pass
                    if docs1:
                        db.save_docs(docs1)


def pushdocs(path, dbs, atomic=True, export=False):
    """ push multiple docs in a path """
    if not isinstance(dbs, (list, tuple)):
        dbs = [dbs]

    docs = []
    for d in os.listdir(path):
        docdir = os.path.join(path, d)
        if docdir.startswith('.'):
            continue
        elif os.path.isfile(docdir):
            if d.endswith(".json"):
                doc = utils.read_json(docdir)
                docid, ext = os.path.splitext(d)
                doc.setdefault('_id', docid)
                doc.setdefault('couchapp', {})
                if not atomic:
                    for db in dbs:
                        db.save_doc(doc, force_update=True)
                else:
                    docs.append(doc)
        else:
            doc = document(docdir, is_ddoc=False)
            if not atomic:
                doc.push(dbs, atomic=False)
            else:
                docs.append(doc)
    if docs:
        if export:
            docs1 = []
            for doc in docs:
                if hasattr(doc, 'doc'):
                    docs1.append(doc.doc())
                else:
                    docs1.append(doc)
            jsonobj = {'docs': docs1}
            return jsonobj
        else:
            for db in dbs:
                docs1 = []
                for doc in docs:
                    if hasattr(doc, 'doc'):
                        docs1.append(doc.doc(db))
                    else:
                        newdoc = doc.copy()
                        try:
                            rev = db.get_rev(doc['_id'])
                            newdoc.update({'_rev': rev})
                        except ResourceNotFound:
                            pass
                        docs1.append(newdoc)
                try:
                    db.save_docs(docs1)
                except BulkSaveError, e:
                    # resolve conflicts
                    docs1 = []
                    for doc in e.errors:
                        try:
                            doc['_rev'] = db.get_rev(doc['_id'])
                            docs1.append(doc)
                        except ResourceNotFound:
                            pass
                if docs1:
                    db.save_docs(docs1)

def clone(db, docid, dest=None, rev=None):
    """
    Clone a CouchDB document to the fs.

    """
    if not dest:
        dest = docid

    path = os.path.normpath(os.path.join(os.getcwd(), dest))
    if not os.path.exists(path):
        os.makedirs(path)

    if not rev:
        doc = db.open_doc(docid)
    else:
        doc = db.open_doc(docid, rev=rev)
    docid = doc['_id']


    metadata = doc.get('couchapp', {})

    # get manifest
    manifest = metadata.get('manifest', {})

    # get signatures
    signatures = metadata.get('signatures', {})

    # get objects refs
    objects = metadata.get('objects', {})

    # create files from manifest
    if manifest:
        for filename in manifest:
            logger.debug("clone property: %s" % filename)
            filepath = os.path.join(path, filename)
            if filename.endswith('/'):
                if not os.path.isdir(filepath):
                    os.makedirs(filepath)
            elif filename == "couchapp.json":
                continue
            else:
                parts = utils.split_path(filename)
                fname = parts.pop()
                v = doc
                while 1:
                    try:
                        for key in parts:
                            v = v[key]
                    except KeyError:
                        break
                    # remove extension
                    last_key, ext = os.path.splitext(fname)

                    # make sure key exist
                    try:
                        content = v[last_key]
                    except KeyError:
                        break


                    if isinstance(content, basestring):
                        _ref = md5(utils.to_bytestring(content)).hexdigest()
                        if objects and _ref in objects:
                            content = objects[_ref]

                        if content.startswith('base64-encoded;'):
                            content = base64.b64decode(content[15:])

                    if fname.endswith('.json'):
                        content = utils.json.dumps(content).encode('utf-8')

                    del v[last_key]

                    # make sure file dir have been created
                    filedir = os.path.dirname(filepath)
                    if not os.path.isdir(filedir):
                        os.makedirs(filedir)

                    utils.write_content(filepath, content)

                    # remove the key from design doc
                    temp = doc
                    for key2 in parts:
                        if key2 == key:
                            if not temp[key2]:
                                del temp[key2]
                            break
                        temp = temp[key2]


    # second pass for missing key or in case
    # manifest isn't in app
    for key in doc.iterkeys():
        if key.startswith('_'):
            continue
        elif key in ('couchapp'):
            app_meta = copy.deepcopy(doc['couchapp'])
            if 'signatures' in app_meta:
                del app_meta['signatures']
            if 'manifest' in app_meta:
                del app_meta['manifest']
            if 'objects' in app_meta:
                del app_meta['objects']
            if 'length' in app_meta:
                del app_meta['length']
            if app_meta:
                couchapp_file = os.path.join(path, 'couchapp.json')
                utils.write_json(couchapp_file, app_meta)
        elif key in ('views'):
            vs_dir = os.path.join(path, key)
            if not os.path.isdir(vs_dir):
                os.makedirs(vs_dir)
            for vsname, vs_item in doc[key].iteritems():
                vs_item_dir = os.path.join(vs_dir, vsname)
                if not os.path.isdir(vs_item_dir):
                    os.makedirs(vs_item_dir)
                for func_name, func in vs_item.iteritems():
                    filename = os.path.join(vs_item_dir, '%s.js' %
                            func_name)
                    utils.write_content(filename, func)
                    logger.warning("clone view not in manifest: %s" % filename)
        elif key in ('shows', 'lists', 'filter', 'update'):
            showpath = os.path.join(path, key)
            if not os.path.isdir(showpath):
                os.makedirs(showpath)
            for func_name, func in doc[key].iteritems():
                filename = os.path.join(showpath, '%s.js' %
                        func_name)
                utils.write_content(filename, func)
                logger.warning(
                    "clone show or list not in manifest: %s" % filename)
        else:
            filedir = os.path.join(path, key)
            if os.path.exists(filedir):
                continue
            else:
                logger.warning("clone property not in manifest: %s" % key)
                if isinstance(doc[key], (list, tuple,)):
                    utils.write_json(filedir + ".json", doc[key])
                elif isinstance(doc[key], dict):
                    if not os.path.isdir(filedir):
                        os.makedirs(filedir)
                    for field, value in doc[key].iteritems():
                        fieldpath = os.path.join(filedir, field)
                        if isinstance(value, basestring):
                            if value.startswith('base64-encoded;'):
                                value = base64.b64decode(content[15:])
                            utils.write_content(fieldpath, value)
                        else:
                            utils.write_json(fieldpath + '.json', value)
                else:
                    value = doc[key]
                    if not isinstance(value, basestring):
                        value = str(value)
                    utils.write_content(filedir, value)

    # save id
    idfile = os.path.join(path, '_id')
    utils.write_content(idfile, doc['_id'])

    utils.write_json(os.path.join(path, '.couchapprc'), {})

    if '_attachments' in doc:  # process attachments
        attachdir = os.path.join(path, '_attachments')
        if not os.path.isdir(attachdir):
            os.makedirs(attachdir)

        for filename in doc['_attachments'].iterkeys():
            if filename.startswith('vendor'):
                attach_parts = utils.split_path(filename)
                vendor_attachdir = os.path.join(path, attach_parts.pop(0),
                        attach_parts.pop(0), '_attachments')
                filepath = os.path.join(vendor_attachdir, *attach_parts)
            else:
                filepath = os.path.join(attachdir, filename)
            filepath = _replace_slash(filepath)
            currentdir = os.path.dirname(filepath)
            if not os.path.isdir(currentdir):
                os.makedirs(currentdir)

            if signatures.get(filename) != utils.sign_file(filepath):
                stream = db.fetch_attachment(docid, filename, stream=True)
                with open(filepath, 'wb') as f:
                    for chunk in stream:
                        f.write(chunk)
                logger.debug("clone attachment: %s" % filename)

    logger.debug("%s/%s cloned in %s" % (db.uri, docid, dest))

def clone_design_doc(source, dest, rev=None):
    """ Clone a design document from it's url like couchapp does.
    """
    try:
        dburl, docid = source.split('_design/')
    except ValueError:
        raise DesignerError("%s isn't a valid source" % source)

    db = client.Database(dburl[:-1], create=False)
    clone(db, docid, dest, rev=rev)

########NEW FILE########
__FILENAME__ = macros
# -*- coding: utf-8 -*-
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

"""
Macros used by loaders. compatible with couchapp. It allow you to include code,
design docs members inside your views, shows and lists.

for example to include a code, add just after first function the line :
    
    // !code relativepath/to/some/code.js
    
To include a member of design doc and use it as a simple javascript object :

    // !json some.member.i.want.to.include
    
All in one, example of a view :

    function(doc) {
        !code _attachments/js/md5.js
        
        if (doc.type == "user") {
            doc.gravatar = hex_md5(user.email);
            emit(doc.username, doc)
        }
    }

This example includes md5.js code and uses md5 function to create gravatar hash
in your views.  So you could just store raw data in your docs and calculate
hash when views are updated.

"""
import glob
from hashlib import md5
import logging
import os
import re

from ..exceptions import MacroError
from ..utils import read_file, read_json, to_bytestring, json

logger = logging.getLogger(__name__)


def package_shows(doc, funcs, app_dir, objs):
   apply_lib(doc, funcs, app_dir, objs)
         
def package_views(doc, views, app_dir, objs):
   for view, funcs in views.iteritems():
       if hasattr(funcs, "items"):
           apply_lib(doc, funcs, app_dir, objs)

def apply_lib(doc, funcs, app_dir, objs):
    for k, v in funcs.items():
        if not isinstance(v, basestring):
            continue
        else:
            logger.debug("process function: %s" % k)
            old_v = v
            try:
                funcs[k] = run_json_macros(doc, 
                    run_code_macros(v, app_dir), app_dir)
            except ValueError, e:
                raise MacroError(
                "Error running !code or !json on function \"%s\": %s" % (k, e))
            if old_v != funcs[k]:
                objs[md5(to_bytestring(funcs[k])).hexdigest()] = old_v
           
def run_code_macros(f_string, app_dir):
   def rreq(mo):
       # just read the file and return it
       path = os.path.join(app_dir, mo.group(2).strip())
       library = ''
       filenum = 0
       for filename in glob.iglob(path):            
           logger.debug("process code macro: %s" % filename)
           try:
               cnt = read_file(filename)
               if cnt.find("!code") >= 0:
                   cnt = run_code_macros(cnt, app_dir)
               library += cnt
           except IOError, e:
               raise MacroError(str(e))
           filenum += 1
           
       if not filenum:
           raise MacroError(
           "Processing code: No file matching '%s'" % mo.group(2))
       return library

   re_code = re.compile('(\/\/|#)\ ?!code (.*)')
   return re_code.sub(rreq, f_string)

def run_json_macros(doc, f_string, app_dir):
   included = {}
   varstrings = []

   def rjson(mo):
       if mo.group(2).startswith('_attachments'): 
           # someone  want to include from attachments
           path = os.path.join(app_dir, mo.group(2).strip())
           filenum = 0
           for filename in glob.iglob(path):
               logger.debug("process json macro: %s" % filename)
               library = ''
               try:
                   if filename.endswith('.json'):
                       library = read_json(filename)
                   else:
                       library = read_file(filename)
               except IOError, e:
                   raise MacroError(str(e))
               filenum += 1
               current_file = filename.split(app_dir)[1]
               fields = current_file.split('/')
               count = len(fields)
               include_to = included
               for i, field in enumerate(fields):
                   if i+1 < count:
                       include_to[field] = {}
                       include_to = include_to[field]
                   else:
                       include_to[field] = library
           if not filenum:
               raise MacroError(
               "Processing code: No file matching '%s'" % mo.group(2))
       else:	
           logger.debug("process json macro: %s" % mo.group(2))
           fields = mo.group(2).strip().split('.')
           library = doc
           count = len(fields)
           include_to = included
           for i, field in enumerate(fields):
               if not field in library:
                   logger.warning(
                   "process json macro: unknown json source: %s" % mo.group(2))
                   break
               library = library[field]
               if i+1 < count:
                   include_to[field] = include_to.get(field, {})
                   include_to = include_to[field]
               else:
                   include_to[field] = library

       return f_string

   def rjson2(mo):
       return '\n'.join(varstrings)

   re_json = re.compile('(\/\/|#)\ ?!json (.*)')
   re_json.sub(rjson, f_string)

   if not included:
       return f_string

   for k, v in included.iteritems():
       varstrings.append("var %s = %s;" % (k, json.dumps(v).encode('utf-8')))

   return re_json.sub(rjson2, f_string)

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

"""
All exceptions used in couchdbkit.
"""
from restkit.errors import ResourceError, RequestFailed

class InvalidAttachment(Exception):
    """ raised when an attachment is invalid """

class DuplicatePropertyError(Exception):
    """ exception raised when there is a duplicate 
    property in a model """

class BadValueError(Exception):
    """ exception raised when a value can't be validated 
    or is required """

class MultipleResultsFound(Exception):
    """ exception raised when more than one object is
    returned by the get_by method"""
    
class NoResultFound(Exception):
    """ exception returned when no results are found """
    
class ReservedWordError(Exception):
    """ exception raised when a reserved word
    is used in Document schema """
    
class DocsPathNotFound(Exception):
    """ exception raised when path given for docs isn't found """
    
class BulkSaveError(Exception):
    """ exception raised when bulk save contain errors.
    error are saved in `errors` property.
    """
    def __init__(self, errors, results, *args):
        self.errors = errors
        self.results = results

class ViewServerError(Exception):
    """ exception raised by view server"""

class MacroError(Exception):
    """ exception raised when macro parsiing error in functions """

class DesignerError(Exception):
    """ unkown exception raised by the designer """

class ResourceNotFound(ResourceError):
    """ Exception raised when resource is not found"""

class ResourceConflict(ResourceError):
    """ Exception raised when there is conflict while updating"""

class PreconditionFailed(ResourceError):
    """ Exception raised when 412 HTTP error is received in response
    to a request """

class DocTypeError(Exception):
    """ Exception raised when doc type of json to be wrapped
    does not match the doc type of the matching class
    """

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
#
# Copyright (c) 2008-2009 Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
# code heavily inspired from django.forms.models
# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer.
#    
#    2. Redistributions in binary form must reproduce the above copyright 
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of Django nor the names of its contributors may be used
#       to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

""" Implement DocumentForm object. It map Document objects to Form and 
works like ModelForm object :

    >>> from couchdbkit.ext.django.forms  import DocumentForm

    # Create the form class.
    >>> class ArticleForm(DocumentForm):
    ...     class Meta:
    ...         model = Article

    # Creating a form to add an article.
    >>> form = ArticleForm()

    # Creating a form to change an existing article.
    >>> article = Article.get(someid)
    >>> form = ArticleForm(instance=article)
    

The generated Form class will have a form field for every model field. 
Each document property has a corresponding default form field:

* StringProperty   ->  CharField,
* IntegerProperty  ->  IntegerField,
* DecimalProperty  ->  DecimalField,
* BooleanProperty  ->  BooleanField,
* FloatProperty    ->  FloatField,
* DateTimeProperty ->  DateTimeField,
* DateProperty     ->  DateField,
* TimeProperty     ->  TimeField


More fields types will be supported soon.
"""


from django.utils.text import capfirst
from django.utils.datastructures import SortedDict
from django.forms.util import ErrorList
from django.forms.forms import BaseForm, get_declared_fields
from django.forms import fields as f
from django.forms.widgets import media_property

FIELDS_PROPERTES_MAPPING = {
    "StringProperty": f.CharField,
    "IntegerProperty": f.IntegerField,
    "DecimalProperty": f.DecimalField,
    "BooleanProperty": f.BooleanField,
    "FloatProperty": f.FloatField,
    "DateTimeProperty": f.DateTimeField,
    "DateProperty": f.DateField,
    "TimeProperty": f.TimeField
}

def document_to_dict(instance, properties=None, exclude=None):
    """
    Returns a dict containing the data in ``instance`` suitable for passing as
    a Form's ``initial`` keyword argument.

    ``properties`` is an optional list of properties names. If provided, 
    only the named properties will be included in the returned dict.

    ``exclude`` is an optional list of properties names. If provided, the named
    properties will be excluded from the returned dict, even if they are listed 
    in the ``properties`` argument.
    """
    # avoid a circular import
    data = {}
    for prop_name in instance._doc.keys():
        if properties and not prop_name in properties:
            continue
        if exclude and prop_name in exclude:
            continue
        data[prop_name] = instance[prop_name]
    return data

def fields_for_document(document, properties=None, exclude=None):
    """
    Returns a ``SortedDict`` containing form fields for the given document.

    ``properties`` is an optional list of properties names. If provided, 
    only the named properties will be included in the returned properties.

    ``exclude`` is an optional list of properties names. If provided, the named
    properties will be excluded from the returned properties, even if 
    they are listed in the ``properties`` argument.
    """
    field_list = []
    
    values = []
    if properties:
        values = [document._properties[prop] for prop in properties if \
                                                prop in document._properties]
    else:
        values = document._properties.values()
        values.sort(lambda a, b: cmp(a.creation_counter, b.creation_counter))
    
    for prop in values: 
        if properties and not prop.name in properties:
            continue
        if exclude and prop.name in exclude:
            continue
        property_class_name = prop.__class__.__name__
        if property_class_name in FIELDS_PROPERTES_MAPPING:
            defaults = {
                'required': prop.required, 
                'label': capfirst(prop.verbose_name), 
            }
            
            if prop.default is not None:
                defaults['initial'] = prop.default_value
                
            if prop.choices:
                if prop.default:
                    defaults['choices'] = prop.default_value() + list(
                                    prop.choices)
                    defaults['coerce'] = prop.to_python
                
            field_list.append((prop.name, 
                FIELDS_PROPERTES_MAPPING[property_class_name](**defaults)))
    return SortedDict(field_list)

class DocumentFormOptions(object):
    def __init__(self, options=None):
        self.document = getattr(options, 'document', None)
        self.properties = getattr(options, 'properties', None)
        self.exclude = getattr(options, 'exclude', None)

class DocumentFormMetaClass(type):
    def __new__(cls, name, bases, attrs):
        try:
            parents = [b for b in bases if issubclass(b, DocumentForm)]
        except NameError:
            # We are defining ModelForm itself.
            parents = None
            
        declared_fields = get_declared_fields(bases, attrs, False)
        new_class = super(DocumentFormMetaClass, cls).__new__(cls, name, bases,
                    attrs)
                
        if not parents:
            return new_class
        
        if 'media' not in attrs:
            new_class.media = media_property(new_class)
    
        opts = new_class._meta = DocumentFormOptions(getattr(new_class, 
                                                'Meta', None))
        
        if opts.document:
            # If a document is defined, extract form fields from it.
            fields = fields_for_document(opts.document, opts.properties,
                                         opts.exclude)
            # Override default docuemnt fields with any custom declared ones
            # (plus, include all the other declared fields).
            fields.update(declared_fields)
        else:
            fields = declared_fields
    
        new_class.declared_fields = declared_fields
        new_class.base_fields = fields
        return new_class
    
class BaseDocumentForm(BaseForm):
    """ Base Document Form object """
    
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None, 
            initial=None, error_class=ErrorList, label_suffix=":",
            empty_permitted=False, instance=None):
            
        opts = self._meta
        
        if instance is None:
            self.instance = opts.document()
            object_data = {}
        else:
            self.instance = instance
            object_data = document_to_dict(instance, opts.properties, 
                                        opts.exclude) 
    
        if initial is not None:
            object_data.update(initial)
            
        super(BaseDocumentForm, self).__init__(data, files, auto_id, prefix, 
                                            object_data, error_class, 
                                            label_suffix, empty_permitted)
                                            
    def save(self, commit=True, dynamic=True):
        """
        Saves this ``form``'s cleaned_data into document instance
        ``self.instance``.

        If commit=True, then the changes to ``instance`` will be saved to the
        database. Returns ``instance``.
        """
        
        opts = self._meta
        cleaned_data = self.cleaned_data.copy()
        for prop_name in self.instance._doc.keys():
            if opts.properties and prop_name not in opts.properties:
                continue
            if opts.exclude and prop_name in opts.exclude:
                continue
            if prop_name in cleaned_data:
                value = cleaned_data.pop(prop_name)
                if value is not None:
                    setattr(self.instance, prop_name, value)
            
        if dynamic:
            for attr_name in cleaned_data.keys():
                if opts.exclude and attr_name in opts.exclude:
                    continue
                value = cleaned_data[attr_name]
                if value is not None:
                    setattr(self.instance, attr_name, value)
    
        if commit:
            self.instance.save()
        
        return self.instance
            
class DocumentForm(BaseDocumentForm):
    """ The document form object """
    __metaclass__ = DocumentFormMetaClass          

########NEW FILE########
__FILENAME__ = loading
# -*- coding: utf-8 -*-
#
# Copyright (c) 2008-2009 Benoit Chesneau <benoitc@e-engura.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
Maintain registry of documents used in your django project
and manage db sessions
"""

import sys
import os

from restkit import BasicAuth
from couchdbkit import Server
from couchdbkit import push
from couchdbkit.resource import CouchdbResource
from couchdbkit.exceptions import ResourceNotFound
from django.conf import settings
from django.utils.datastructures import SortedDict

COUCHDB_DATABASES = getattr(settings, "COUCHDB_DATABASES", [])
COUCHDB_TIMEOUT = getattr(settings, "COUCHDB_TIMEOUT", 300)

class CouchdbkitHandler(object):
    """ The couchdbkit handler for django """

    # share state between instances
    __shared_state__ = dict(
            _databases = {},
            app_schema = SortedDict()
    )

    def __init__(self, databases):
        """ initialize couchdbkit handler with COUCHDB_DATABASES
        settings """

        self.__dict__ = self.__shared_state__

        # Convert old style to new style
        if isinstance(databases, (list, tuple)):
            databases = dict(
                (app_name, {'URL': uri}) for app_name, uri in databases
            )

        # create databases sessions
        for app_name, app_setting in databases.iteritems():
            uri = app_setting['URL']

            # Do not send credentials when they are both None as admin party will give a 401
            user = app_setting.get('USER')
            password = app_setting.get('PASSWORD')
            filters = [BasicAuth(user, password)] if (user or password) is not None else []

            try:
                if isinstance(uri, (list, tuple)):
                    # case when you want to specify server uri
                    # and database name specifically. usefull
                    # when you proxy couchdb on some path
                    server_uri, dbname = uri
                else:
                    server_uri, dbname = uri.rsplit("/", 1)
            except ValueError:
                raise ValueError("couchdb uri [%s:%s] invalid" % (
                    app_name, uri))

            res = CouchdbResource(server_uri, timeout=COUCHDB_TIMEOUT, filters=filters)

            server = Server(server_uri, resource_instance=res)
            app_label = app_name.split('.')[-1]
            self._databases[app_label] = (server, dbname)

    def sync(self, app, verbosity=2, temp=None):
        """ used to sync views of all applications and eventually create
        database.

        When temp is specified, it is appended to the app's name on the docid.
        It can then be updated in the background and copied over the existing
        design docs to reduce blocking time of view updates """
        app_name = app.__name__.rsplit('.', 1)[0]
        app_labels = set()
        schema_list = self.app_schema.values()
        for schema_dict in schema_list:
            for schema in schema_dict.values():
                app_module = schema.__module__.rsplit(".", 1)[0]
                if app_module == app_name and not schema._meta.app_label in app_labels:
                    app_labels.add(schema._meta.app_label)
        for app_label in app_labels:
            if not app_label in self._databases:
                continue
            if verbosity >=1:
                print "sync `%s` in CouchDB" % app_name
            db = self.get_db(app_label)

            app_path = os.path.abspath(os.path.join(sys.modules[app.__name__].__file__, ".."))
            design_path = "%s/%s" % (app_path, "_design")
            if not os.path.isdir(design_path):
                if settings.DEBUG:
                    print >>sys.stderr, "%s don't exists, no ddoc synchronized" % design_path
                return

            if temp:
                design_name = '%s-%s' % (app_label, temp)
            else:
                design_name = app_label

            docid = "_design/%s" % design_name

            push(os.path.join(app_path, "_design"), db, force=True,
                    docid=docid)

            if temp:
                ddoc = db[docid]
                view_names = ddoc.get('views', {}).keys()
                if len(view_names) > 0:
                    if verbosity >= 1:
                        print 'Triggering view rebuild'

                    view = '%s/%s' % (design_name, view_names[0])
                    list(db.view(view, limit=0))


    def copy_designs(self, app, temp, verbosity=2, delete=True):
        """ Copies temporary view over the existing ones

        This is used to reduce the waiting time for blocking view updates """

        app_name = app.__name__.rsplit('.', 1)[0]
        app_labels = set()
        schema_list = self.app_schema.values()
        for schema_dict in schema_list:
            for schema in schema_dict.values():
                app_module = schema.__module__.rsplit(".", 1)[0]
                if app_module == app_name and not schema._meta.app_label in app_labels:
                    app_labels.add(schema._meta.app_label)
        for app_label in app_labels:
            if not app_label in self._databases:
                continue
            if verbosity >=1:
                print "Copy prepared design docs for `%s`" % app_name
            db = self.get_db(app_label)

            tmp_name = '%s-%s' % (app_label, temp)

            from_id = '_design/%s' % tmp_name
            to_id   = '_design/%s' % app_label

            try:
                db.copy_doc(from_id, to_id)

                if delete:
                    del db[from_id]

            except ResourceNotFound:
                print '%s not found.' % (from_id, )
                return


    def get_db(self, app_label, register=False):
        """ retrieve db session for a django application """
        if register:
            return

        db = self._databases[app_label]
        if isinstance(db, tuple):
            server, dbname = db
            db = server.get_or_create_db(dbname)
            self._databases[app_label] = db
        return db

    def register_schema(self, app_label, *schema):
        """ register a Document object"""
        for s in schema:
            schema_name = schema[0].__name__.lower()
            schema_dict = self.app_schema.setdefault(app_label, SortedDict())
            if schema_name in schema_dict:
                fname1 = os.path.abspath(sys.modules[s.__module__].__file__)
                fname2 = os.path.abspath(sys.modules[schema_dict[schema_name].__module__].__file__)
                if os.path.splitext(fname1)[0] == os.path.splitext(fname2)[0]:
                    continue
            schema_dict[schema_name] = s

    def get_schema(self, app_label, schema_name):
        """ retriev Document object from its name and app name """
        return self.app_schema.get(app_label, SortedDict()).get(schema_name.lower())

couchdbkit_handler = CouchdbkitHandler(COUCHDB_DATABASES)
register_schema = couchdbkit_handler.register_schema
get_schema = couchdbkit_handler.get_schema
get_db = couchdbkit_handler.get_db

########NEW FILE########
__FILENAME__ = sync_couchdb
from django.db.models import get_apps
from django.core.management.base import BaseCommand
from couchdbkit.ext.django.loading import couchdbkit_handler

class Command(BaseCommand):
    help = 'Sync couchdb views.'

    def handle(self, *args, **options):
        for app in get_apps():
            couchdbkit_handler.sync(app, verbosity=2)

########NEW FILE########
__FILENAME__ = sync_finish_couchdb
from django.db.models import get_apps
from django.core.management.base import BaseCommand
from couchdbkit.ext.django.loading import couchdbkit_handler

class Command(BaseCommand):
    help = 'Copy temporary design docs over existing ones'

    def handle(self, *args, **options):
        for app in get_apps():
            couchdbkit_handler.copy_designs(app, temp='tmp', verbosity=2)

########NEW FILE########
__FILENAME__ = sync_prepare_couchdb
from django.db.models import get_apps
from django.core.management.base import BaseCommand
from couchdbkit.ext.django.loading import couchdbkit_handler

class Command(BaseCommand):
    help = 'Sync design docs to temporary ids'

    def handle(self, *args, **options):
        for app in get_apps():
            couchdbkit_handler.sync(app, verbosity=2, temp='tmp')

########NEW FILE########
__FILENAME__ = schema
# -*- coding: utf-8 -*-
#
# Copyright (c) 2008-2009 Benoit Chesneau <benoitc@e-engura.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

""" Wrapper of couchdbkit Document and Properties for django. It also
add possibility to a document to register itself in CouchdbkitHandler
"""
import re
import sys

from django.conf import settings
from django.db.models.options import get_verbose_name
from django.utils.translation import activate, deactivate_all, get_language, \
string_concat
from django.utils.encoding import smart_str, force_unicode

from couchdbkit import schema
from couchdbkit.ext.django.loading import get_schema, register_schema, \
get_db

__all__ = ['Property', 'StringProperty', 'IntegerProperty',
            'DecimalProperty', 'BooleanProperty', 'FloatProperty',
            'DateTimeProperty', 'DateProperty', 'TimeProperty',
            'dict_to_json', 'list_to_json', 'value_to_json',
            'value_to_python', 'dict_to_python', 'list_to_python',
            'convert_property', 'DocumentSchema', 'Document',
            'SchemaProperty', 'SchemaListProperty', 'ListProperty',
            'DictProperty', 'StringDictProperty', 'StringListProperty',
            'SchemaDictProperty', 'SetProperty',]


DEFAULT_NAMES = ('verbose_name', 'db_table', 'ordering',
                 'app_label')

class Options(object):
    """ class based on django.db.models.options. We only keep
    useful bits."""

    def __init__(self, meta, app_label=None):
        self.module_name, self.verbose_name = None, None
        self.verbose_name_plural = None
        self.object_name, self.app_label = None, app_label
        self.meta = meta
        self.admin = None

    def contribute_to_class(self, cls, name):
        cls._meta = self
        self.installed = re.sub('\.models$', '', cls.__module__) in settings.INSTALLED_APPS
        # First, construct the default values for these options.
        self.object_name = cls.__name__
        self.module_name = self.object_name.lower()
        self.verbose_name = get_verbose_name(self.object_name)

        # Next, apply any overridden values from 'class Meta'.
        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name in self.meta.__dict__:
                # Ignore any private attributes that Django doesn't care about.
                # NOTE: We can't modify a dictionary's contents while looping
                # over it, so we loop over the *original* dictionary instead.
                if name.startswith('_'):
                    del meta_attrs[name]
            for attr_name in DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))

            # verbose_name_plural is a special case because it uses a 's'
            # by default.
            setattr(self, 'verbose_name_plural', meta_attrs.pop('verbose_name_plural', string_concat(self.verbose_name, 's')))

            # Any leftover attributes must be invalid.
            if meta_attrs != {}:
                raise TypeError("'class Meta' got invalid attribute(s): %s" % ','.join(meta_attrs.keys()))
        else:
            self.verbose_name_plural = string_concat(self.verbose_name, 's')
        del self.meta

    def __str__(self):
        return "%s.%s" % (smart_str(self.app_label), smart_str(self.module_name))

    def verbose_name_raw(self):
        """
        There are a few places where the untranslated verbose name is needed
        (so that we get the same value regardless of currently active
        locale).
        """
        lang = get_language()
        deactivate_all()
        raw = force_unicode(self.verbose_name)
        activate(lang)
        return raw
    verbose_name_raw = property(verbose_name_raw)

class DocumentMeta(schema.SchemaProperties):
    def __new__(cls, name, bases, attrs):
        super_new = super(DocumentMeta, cls).__new__
        parents = [b for b in bases if isinstance(b, DocumentMeta)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        new_class = super_new(cls, name, bases, attrs)
        attr_meta = attrs.pop('Meta', None)
        if not attr_meta:
            meta = getattr(new_class, 'Meta', None)
        else:
            meta = attr_meta

        if getattr(meta, 'app_label', None) is None:
            document_module = sys.modules[new_class.__module__]
            app_label = document_module.__name__.split('.')[-2]
        else:
            app_label = getattr(meta, 'app_label')

        new_class.add_to_class('_meta', Options(meta, app_label=app_label))

        register_schema(app_label, new_class)

        return get_schema(app_label, name)

    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)

class Document(schema.Document):
    """ Document object for django extension """
    __metaclass__ = DocumentMeta

    get_id = property(lambda self: self['_id'])
    get_rev = property(lambda self: self['_rev'])

    @classmethod
    def get_db(cls):
        db = getattr(cls, '_db', None)
        if db is None:
            app_label = getattr(cls._meta, "app_label")
            db = get_db(app_label)
            cls._db = db
        return db

DocumentSchema = schema.DocumentSchema

#  properties
Property = schema.Property
StringProperty = schema.StringProperty
IntegerProperty = schema.IntegerProperty
DecimalProperty = schema.DecimalProperty
BooleanProperty = schema.BooleanProperty
FloatProperty = schema.FloatProperty
DateTimeProperty = schema.DateTimeProperty
DateProperty = schema.DateProperty
TimeProperty = schema.TimeProperty
SchemaProperty = schema.SchemaProperty
SchemaListProperty = schema.SchemaListProperty
ListProperty = schema.ListProperty
DictProperty = schema.DictProperty
StringDictProperty = schema.StringDictProperty
StringListProperty = schema.StringListProperty
SchemaDictProperty = schema.SchemaDictProperty
SetProperty = schema.SetProperty



# some utilities
dict_to_json = schema.dict_to_json
list_to_json = schema.list_to_json
value_to_json = schema.value_to_json
value_to_python = schema.value_to_python
dict_to_python = schema.dict_to_python
list_to_python = schema.list_to_python
convert_property = schema.convert_property

########NEW FILE########
__FILENAME__ = testrunner
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings

from . import loading
from ...exceptions import ResourceNotFound

class CouchDbKitTestSuiteRunner(DjangoTestSuiteRunner):
    """
    A test suite runner for couchdbkit.  This offers the exact same functionality
    as the default django test suite runner, except that it connects all the couchdbkit
    django-extended models to a test database.  The test database is deleted at the
    end of the tests.  To use this, just add this file to your project and the following 
    line to your settings.py file:
    
    TEST_RUNNER = 'myproject.testrunner.CouchDbKitTestSuiteRunner'
    """
    
    dbs = []

    def get_test_db_name(self, dbname):
        return "%s_test" % dbname

    def get_test_db(self, db):
        # not copying DB would modify the db dict and add multiple "_test"
        test_db = db.copy()
        test_db['URL'] = self.get_test_db_name(test_db['URL'])
        return test_db

    def setup_databases(self, **kwargs):
        print "overridding the couchdbkit database settings to use a test database!"
                 
        # first pass: just implement this as a monkey-patch to the loading module
        # overriding all the existing couchdb settings
        databases = getattr(settings, "COUCHDB_DATABASES", [])

        # Convert old style to new style
        if isinstance(databases, (list, tuple)):
            databases = dict(
                (app_name, {'URL': uri}) for app_name, uri in databases
            )

        self.dbs = dict(
            (app, self.get_test_db(db)) for app, db in databases.items()
        )

        old_handler = loading.couchdbkit_handler
        couchdbkit_handler = loading.CouchdbkitHandler(self.dbs)
        loading.couchdbkit_handler = couchdbkit_handler
        loading.register_schema = couchdbkit_handler.register_schema
        loading.get_schema = couchdbkit_handler.get_schema
        loading.get_db = couchdbkit_handler.get_db
        
        # register our dbs with the extension document classes
        for app, value in old_handler.app_schema.items():
            for name, cls in value.items():
                cls.set_db(loading.get_db(app))
                                
                
        return super(CouchDbKitTestSuiteRunner, self).setup_databases(**kwargs)
    
    def teardown_databases(self, old_config, **kwargs):
        deleted_databases = []
        skipcount = 0
        for app in self.dbs:
            app_label = app.split('.')[-1]
            db = loading.get_db(app_label)
            if db.dbname in deleted_databases: 
                skipcount += 1
                continue
            try:
                db.server.delete_db(db.dbname)
                deleted_databases.append(db.dbname)
                print "deleted database %s for %s" % (db.dbname, app_label)
            except ResourceNotFound:
                print "database %s not found for %s! it was probably already deleted." % (db.dbname, app_label)
        if skipcount:
            print "skipped deleting %s app databases that were already deleted" % skipcount
        return super(CouchDbKitTestSuiteRunner, self).teardown_databases(old_config, **kwargs)

########NEW FILE########
__FILENAME__ = adapters
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

from repoze.what.adapters import BaseSourceAdapter
from repoze.who.interfaces import IAuthenticator
from repoze.who.interfaces import IMetadataProvider
from zope.interface import implements

class GroupAdapter(BaseSourceAdapter):
    """ group adapter """

    def __init__(self, user_class):
        self.user_class = user_class

    def _get_all_sections(self):
        raise NotImplementedError()

    def _get_section_items(self, section):
        raise NotImplementedError()

    def _find_sections(self, hint):
        """Returns the group ids that the user is part of."""
        user = self.user_class.get(hint['repoze.what.userid'])
        return user.groups

    def _include_items(self, section, items):
        raise NotImplementedError()

    def _item_is_included(self, section, item):
        raise NotImplementedError()

    def _section_exists(self, section):
        raise NotImplementedError()

class PermissionAdapter(BaseSourceAdapter):
    def __init__(self, db):
        self.db = db

    def _get_all_sections(self):
        raise NotImplementedError()

    def _get_section_items(self, section):
        raise NotImplementedError()

    def _find_sections(self, hint):
        results = self.db.view('group/show_permissions', startkey=hint).all()
        return [x["value"] for x in results]

    def _include_items(self, section, items):
        raise NotImplementedError()

    def _item_is_included(self, section, item):
        raise NotImplementedError()

    def _section_exists(self, section):
        raise NotImplementedError()

class Authenticator(object):
    implements(IAuthenticator)

    def __init__(self, user_class):
        self.user_class = user_class

    def authenticate(self, environ, identity):
        login = identity.get('login', '')
        password = identity.get('password', '')

        user = self.user_class.authenticate(login, password)
        if not user:
            return None
        identity['login'] = str(user.login)
        identity['user'] = user
        return user._id

class MDPlugin(object):
    implements(IMetadataProvider)

    def __init__(self, user_class):
        self.user_class = user_class

    def add_metadata(self, environ, identity):
        if 'user' not in identity:
            uid = identity['repoze.who.userid']
            if uid:
                user = self.user_class.get(uid)
                identity['user'] = user

########NEW FILE########
__FILENAME__ = basic
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import logging
from paste.request import parse_dict_querystring, parse_formvars
from paste.httpexceptions import HTTPUnauthorized
from paste.httpheaders import CONTENT_LENGTH, CONTENT_TYPE
from repoze.what.middleware import setup_auth
from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
from repoze.who.interfaces import IChallenger, IIdentifier

import sys
from zope.interface import implements

from .adapters import GroupAdapter, PermissionAdapter, \
Authenticator, MDPlugin


class BasicAuth(object):
    """A basic challenger and identifier"""
    implements(IChallenger, IIdentifier)

    def __init__(self, login_url="/user/login", logout_url="/user/logout"):
        self._login_url = login_url
        self._logout_url = logout_url

    def identify(self, environ):
        path_info = environ['PATH_INFO']
        query = parse_dict_querystring(environ)

        # This will handle the logout request.
        if path_info == self._logout_url:
            # set in environ for self.challenge() to find later
            environ['repoze.who.application'] = HTTPUnauthorized()
            return None
        elif path_info == self._login_url:
            form = parse_formvars(environ)
            form.update(query)
            try:
                credentials = {
                    'login': form['login'],
                    'password': form['password']
                }
            except KeyError:
                credentials = None

            def auth_resp(environ, start_response):
                import json
                resp = {
                    "success": True
                }

                resp_str = json.dumps(resp)

                content_length = CONTENT_LENGTH.tuples(str(len(resp_str)))
                content_type = CONTENT_TYPE.tuples('application/json')
                headers = content_length + content_type
                start_response('200 OK', headers)
                return [resp_str]

            environ['repoze.who.application'] = auth_resp
            return credentials

    def challenge(self, environ, status, app_headers, forget_headers):
        cookies = [(h,v) for (h,v) in app_headers if h.lower() == 'set-cookie']
        if not forget_headers:
            return HTTPUnauthorized()

        def auth_form(environ, start_response):
            towrite = "Challenging this"
            content_length = CONTENT_LENGTH.tuples(str(len(towrite)))
            content_type = CONTENT_TYPE.tuples('text/html')
            headers = content_length + content_type + forget_headers
            start_response('200 OK', headers)
            return [towrite]
        return auth_form

    def remember(self, environ, identity):
        return environ['repoze.who.plugins']['cookie'].remember(environ, identity)

    def forget(self, environ, identity):
        return environ['repoze.who.plugins']['cookie'].forget(environ, identity)

def AuthBasicMiddleware(app, conf, user_class):
    groups = GroupAdapter(user_class)
    groups = {'all_groups': groups}
    permissions = {'all_perms': PermissionAdapter(conf["couchdb.db"])}

    basicauth = BasicAuth()
    cookie = AuthTktCookiePlugin(conf['cookies.secret'])

    who_args = {}
    who_args['authenticators'] = [('accounts', Authenticator(user_class))]
    who_args['challengers'] = [('basicauth', basicauth)]
    who_args['identifiers'] = [('basicauth', basicauth), ('cookie', cookie)]
    who_args['mdproviders'] = [('accounts', MDPlugin(user_class))]
    who_args['log_stream'] = sys.stdout
    who_args['log_level'] = logging.DEBUG

    return setup_auth(app, groups, permissions, **who_args)


########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

from hashlib import sha256
import os


from .... import Document, SchemaListProperty, StringProperty, \
StringListProperty

class Permission(Document):
    name = StringProperty(required=True)

class Group(Document):
    """
    Group class, contains multiple permissions.
    """
    name = StringProperty(required=True)
    permissions = SchemaListProperty(Permission)

class User(Document):
    """The base User model. This should be extended by the user."""
    login = StringProperty(required=True)
    password = StringProperty(required=True)
    groups = StringListProperty()

    @staticmethod
    def _hash_password(cleartext):
        if isinstance(cleartext, unicode):
            password_8bit = cleartext.encode('UTF-8')
        else:
            password_8bit = cleartext

        salt = sha256()
        salt.update(os.urandom(60))
        hash = sha256()
        hash.update(password_8bit + salt.hexdigest())
        hashed_password = salt.hexdigest() + hash.hexdigest()

        if not isinstance(hashed_password, unicode):
            hashed_password = hashed_password.decode('UTF-8')
        return hashed_password

    def set_password(self, password):
        self.password = self._hash_password(password)

    @staticmethod
    def authenticate(login, password):
        user = User.view("user/by_login", key=login).one()
        if not user:
            return None

        hashed_pass = sha256()
        hashed_pass.update(password + user.password[:64])
        if user.password[64:] != hashed_pass.hexdigest():
            return None
        return user


########NEW FILE########
__FILENAME__ = commands
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import os
from paste.deploy import loadapp
from paste.script.command import Command

from .db import sync_design, default_design_path

class SyncDbCommand(Command):
    """Syncs the CouchDB views on disk with the database.

    Example::

        $ paster syncdb my-development.ini

    This will also create the database if it does not exist
    """
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__

    min_args = 1
    max_args = 1
    group_name = 'couchdbkit'
    default_verbosity = 3
    parser = Command.standard_parser(simulate=True)

    def command(self):
        """Main command to sync db"""
        config_file = self.args[0]

        config_name = 'config:%s' % config_file
        here_dir = os.getcwd()

        if not self.options.quiet:
            # Configure logging from the config file
            self.logging_file_config(config_file)

        # Load the wsgi app first so that everything is initialized right
        wsgiapp = loadapp(config_name, relative_to=here_dir)
        try:
            design_path = wsgiapp.config['couchdb.design']
        except KeyError:
            design_path = default_design_path(wsgiapp.config)

        # This syncs the main database.
        sync_design(wsgiapp.config['couchdb.db'], design_path)


########NEW FILE########
__FILENAME__ = db
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import os.path

from ...client import Server
from ...designer import pushapps
from ...schema import Document

def init_from_config(config):
    """Initialize the database given a pylons config. This assumes the
    configuration format layed out on the wiki. This will only initialize the
    primary database.

    This prefixes the database name with test_ if we're running unit tests.
    """
    uri = config['couchdb.uri']
    dbname = config['couchdb.dbname']

    config['couchdb.db'] = init_db(uri, dbname)
    config['couchdb.fixtures'] = os.path.join(config['pylons.paths']['root'], "fixtures")

def init_db(uri, dbname, main_db=True):
    """Returns a db object and syncs the design documents on demand.
    If main_db is set to true then all models will use that one by default.
    """
    server = Server(uri)

    db = server.get_or_create_db(dbname)
    if main_db:
        Document.set_db(db)
    return db

def sync_design(db, path):
    """Synchronizes the design documents with the database passed in."""
    pushapps(path, db)

def default_design_path(config):
    """Returns full path to the default design documents path, it's _design in
    the pylons root path
    """
    return os.path.join(config['pylons.paths']['root'], "_design")


########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import os
import unittest

from ... import BaseDocsLoader, ResourceNotFound
from .db import init_db, sync_design, default_design_path
from ...utils import json

class FixtureLoader(BaseDocsLoader):
    def __init__(self, directory):
        self._directory = directory

    def get_docs(self):
        docs = []
        for fixture in os.listdir(self._directory):
            fixture_path = os.path.join(self._directory, fixture)
            if not os.path.isfile(fixture_path):
                raise Exception("Fixture path %s not found" % fixture_path)
            with open(fixture_path, "r") as fp:
                for doc in json.load(fp):
                    docs.append(doc)
        return docs

class TestCase(unittest.TestCase):
    """
    Basic test class that will be default load all fixtures specified in the
    fixtures attribute.
    """
    def __init__(self, *args, **kwargs):
        self._config = kwargs['config']
        del kwargs['config']
        unittest.TestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        dbname = self._config['couchdb.db'].dbname

        # Set the directory to the fixtures.
        try:
            self._config['couchdb.db'].server.delete_db(dbname)
        except ResourceNotFound:
            pass

        self._config['couchdb.db'] = init_db(self._config['couchdb.uri'], dbname)
        sync_design(self._config['couchdb.db'], default_design_path(self._config))

        if hasattr(self, 'fixtures'):
            fixtures_dir = self._config['couchdb.fixtures']
            if not os.path.isdir(fixtures_dir):
                raise Exception("Fixtures dir %s not found" % fixtures_dir)
            FixtureLoader(fixtures_dir).sync(self._config['couchdb.db'])


########NEW FILE########
__FILENAME__ = external
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import sys

from .utils import json

class External(object):
    """ simple class to handle an external
    ans send the response.
    
    example:
    
        from couchdbkit.external import External
        from couchdbkit.utils import json 

        class Test(External):

            def handle_line(self, line):
                self.send_response(200, 
                    "got message external object %s" % json.dumps(line),
                    {"Content-type": "text/plain"})

        if __name__ == "__main__":
            Test().run()
        
    """

    def __init__(self, stdin=sys.stdin, stdout=sys.stdout):
        self.stdin = stdin
        self.stdout = stdout
        
    def handle_line(self, line):
        raise NotImplementedError
        
    def write(self, line):
        self.stdout.write("%s\n" % line)
        self.stdout.flush()
        
    def lines(self):
        line = self.stdin.readline()
        while line:
            yield json.loads(line)
            line = self.stdin.readline()
    
    def run(self):
        for line in self.lines():
            self.handle_line(line)
            
    def send_response(self, code=200, body="", headers={}):
        resp = {
            'code': code, 
            'body': body, 
            'headers': headers
        }
        self.write(json.dumps(resp))

########NEW FILE########
__FILENAME__ = loaders
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

"""
Loaders are a simple way to manage design docs in your Python application. 
Loaders are compatible with couchapp script (http://github.com/couchapp/couchapp).
So it means that you can simply use couchdbkit as replacement for your python
applications with advantages of couchdbkit client. Compatibility with couchapp means that
you can also use macros to include javascript code or design doc members in your views,
shows & lists.

Loaders are FileSystemDocsLoader and FileSystemDocLoader. The first
one takes a directory and retrieve all design docs before sending them to
CouchDB. Second allow you to send only one design doc.

This module is here for compatibility reason and will be removed in 0.6.
It's replaced by couchdbkit.designer module and push* functions.
"""
from __future__ import with_statement

from .designer import document, push, pushapps, pushdocs

class BaseDocsLoader(object):
    """Baseclass for all doc loaders. """
   
    def get_docs(self):
        raise NotImplementedError

    def sync(self, dbs, atomic=True, **kwargs):
        raise NotImplementedError

class FileSystemDocsLoader(BaseDocsLoader):
    """ Load docs from the filesystem. This loader can find docs
    in folders on the filesystem and is the preferred way to load them. 
    
    The loader takes the path for design docs as a string  or if multiple
    locations are wanted a list of them which is then looked up in the
    given order:

    >>> loader = FileSystemDocsLoader('/path/to/templates')
    >>> loader = FileSystemDocsLoader(['/path/to/templates', '/other/path'])
    
    You could also do the same to loads docs.
    """

    def __init__(self, designpath, docpath=None):
        if isinstance(designpath, basestring):
            self.designpaths = [designpath]
        else:
            self.designpaths = designpath

        docpath = docpath or []
        if isinstance(docpath, basestring):
            docpath = [docpath]
        self.docpaths = docpath            
        

    def get_docs(self):
        docs = []
        for path in self.docpaths:
            ret = pushdocs(path, [], export=True)
            docs.extend(ret['docs'])

        for path in self.designpaths:
            ret = pushapps(path, [], export=True)
            docs.extend(ret['docs'])
        return docs

        
    def sync(self, dbs, atomic=True, **kwargs):
        for path in self.docpaths:
            pushdocs(path, dbs, atomic=atomic)

        for path in self.designpaths:
            pushapps(path, dbs, atomic=atomic)
 
class FileSystemDocLoader(BaseDocsLoader):
    """ Load only one design doc from a path on the filesystem.
        
        >>> loader = FileSystemDocLoader("/path/to/designdocfolder", "nameodesigndoc")
    """
    
    def __init__(self, designpath, name, design_name=None):
        self.designpath = designpath
        self.name = name
        if not design_name.startswith("_design"):
            design_name = "_design/%s" % design_name
        self.design_name = design_name

    def get_docs(self):
        return document(self.design_path, create=False,
                docid=self.design_name)

    def sync(self, dbs, atomic=True, **kwargs):
        push(self.design_path, dbs, atomic=atomic,
                docid=self.design_name)


########NEW FILE########
__FILENAME__ = resource
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

"""
couchdb.resource
~~~~~~~~~~~~~~~~~~~~~~

This module providess a common interface for all CouchDB request. This
module makes HTTP request using :mod:`httplib2` module or :mod:`pycurl`
if available. Just use set transport argument for this.

Example:

    >>> resource = CouchdbResource()
    >>> info = resource.get()
    >>> info['couchdb']
    u'Welcome'

"""
import base64
import re

from restkit import Resource, ClientResponse
from restkit.errors import ResourceError, RequestFailed, RequestError
from restkit.util import url_quote

from . import __version__
from .exceptions import ResourceNotFound, ResourceConflict, \
PreconditionFailed
from .utils import json

USER_AGENT = 'couchdbkit/%s' % __version__

RequestFailed = RequestFailed

class CouchDBResponse(ClientResponse):

    @property
    def json_body(self):
        body = self.body_string()

        # try to decode json
        try:
            return json.loads(body)
        except ValueError:
            return body


class CouchdbResource(Resource):

    def __init__(self, uri="http://127.0.0.1:5984", **client_opts):
        """Constructor for a `CouchdbResource` object.

        CouchdbResource represent an HTTP resource to CouchDB.

        @param uri: str, full uri to the server.
        """
        client_opts['response_class'] = CouchDBResponse

        Resource.__init__(self, uri=uri, **client_opts)
        self.safe = ":/%"

    def copy(self, path=None, headers=None, **params):
        """ add copy to HTTP verbs """
        return self.request('COPY', path=path, headers=headers, **params)

    def request(self, method, path=None, payload=None, headers=None, **params):
        """ Perform HTTP call to the couchdb server and manage
        JSON conversions, support GET, POST, PUT and DELETE.

        Usage example, get infos of a couchdb server on
        http://127.0.0.1:5984 :


            import couchdbkit.CouchdbResource
            resource = couchdbkit.CouchdbResource()
            infos = resource.request('GET')

        @param method: str, the HTTP action to be performed:
            'GET', 'HEAD', 'POST', 'PUT', or 'DELETE'
        @param path: str or list, path to add to the uri
        @param data: str or string or any object that could be
            converted to JSON.
        @param headers: dict, optional headers that will
            be added to HTTP request.
        @param raw: boolean, response return a Response object
        @param params: Optional parameterss added to the request.
            Parameterss are for example the parameters for a view. See
            `CouchDB View API reference
            <http://wiki.apache.org/couchdb/HTTP_view_API>`_ for example.

        @return: tuple (data, resp), where resp is an `httplib2.Response`
            object and data a python object (often a dict).
        """

        headers = headers or {}
        headers.setdefault('Accept', 'application/json')
        headers.setdefault('User-Agent', USER_AGENT)

        if payload is not None:
            #TODO: handle case we want to put in payload json file.
            if not hasattr(payload, 'read') and not isinstance(payload, basestring):
                payload = json.dumps(payload).encode('utf-8')
                headers.setdefault('Content-Type', 'application/json')

        params = encode_params(params)
        try:
            resp = Resource.request(self, method, path=path,
                             payload=payload, headers=headers, **params)

        except ResourceError, e:
            msg = getattr(e, 'msg', '')
            if e.response and msg:
                if e.response.headers.get('content-type') == 'application/json':
                    try:
                        msg = json.loads(msg)
                    except ValueError:
                        pass

            if type(msg) is dict:
                error = msg.get('reason')
            else:
                error = msg

            if e.status_int == 404:
                raise ResourceNotFound(error, http_code=404,
                        response=e.response)

            elif e.status_int == 409:
                raise ResourceConflict(error, http_code=409,
                        response=e.response)
            elif e.status_int == 412:
                raise PreconditionFailed(error, http_code=412,
                        response=e.response)
            else:
                raise
        except:
            raise

        return resp

def encode_params(params):
    """ encode parameters in json if needed """
    _params = {}
    if params:
        for name, value in params.items():
            if name in ('key', 'startkey', 'endkey'):
                value = json.dumps(value)
            elif value is None:
                continue
            elif not isinstance(value, basestring):
                value = json.dumps(value)
            _params[name] = value
    return _params

def escape_docid(docid):
    if docid.startswith('/'):
        docid = docid[1:]
    if docid.startswith('_design'):
        docid = '_design/%s' % url_quote(docid[8:], safe='')
    else:
        docid = url_quote(docid, safe='')
    return docid

re_sp = re.compile('\s')
def encode_attachments(attachments):
    for k, v in attachments.iteritems():
        if v.get('stub', False):
            continue
        else:
            v['data'] = re_sp.sub('', base64.b64encode(v['data']))
    return attachments

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

""" module that provides a Document object that allows you
to map CouchDB document in Python statically, dynamically or both
"""


from . import properties as p
from .properties import value_to_python, \
convert_property, MAP_TYPES_PROPERTIES, ALLOWED_PROPERTY_TYPES, \
LazyDict, LazyList
from ..exceptions import DuplicatePropertyError, ResourceNotFound, \
ReservedWordError


__all__ = ['ReservedWordError', 'ALLOWED_PROPERTY_TYPES', 'DocumentSchema',
        'SchemaProperties', 'DocumentBase', 'QueryMixin', 'AttachmentMixin',
        'Document', 'StaticDocument', 'valid_id']

_RESERVED_WORDS = ['_id', '_rev', '$schema']

_NODOC_WORDS = ['doc_type']


def check_reserved_words(attr_name):
    if attr_name in _RESERVED_WORDS:
        raise ReservedWordError(
            "Cannot define property using reserved word '%(attr_name)s'." %
            locals())

def valid_id(value):
    if isinstance(value, basestring) and not value.startswith('_'):
        return value
    raise TypeError('id "%s" is invalid' % value)

class SchemaProperties(type):

    def __new__(cls, name, bases, attrs):
        # init properties
        properties = {}
        defined = set()
        for base in bases:
            if hasattr(base, '_properties'):
                property_keys = base._properties.keys()
                duplicate_properties = defined.intersection(property_keys)
                if duplicate_properties:
                    raise DuplicatePropertyError(
                        'Duplicate properties in base class %s already defined: %s' % (base.__name__, list(duplicate_properties)))
                defined.update(property_keys)
                properties.update(base._properties)

        doc_type = attrs.get('doc_type', False)
        if not doc_type:
            doc_type = name
        else:
            del attrs['doc_type']

        attrs['_doc_type'] = doc_type

        for attr_name, attr in attrs.items():
            # map properties
            if isinstance(attr, p.Property):
                check_reserved_words(attr_name)
                if attr_name in defined:
                    raise DuplicatePropertyError('Duplicate property: %s' % attr_name)
                properties[attr_name] = attr
                attr.__property_config__(cls, attr_name)
            # python types
            elif type(attr) in MAP_TYPES_PROPERTIES and \
                    not attr_name.startswith('_') and \
                    attr_name not in _NODOC_WORDS:
                check_reserved_words(attr_name)
                if attr_name in defined:
                    raise DuplicatePropertyError('Duplicate property: %s' % attr_name)
                prop = MAP_TYPES_PROPERTIES[type(attr)](default=attr)
                properties[attr_name] = prop
                prop.__property_config__(cls, attr_name)
                attrs[attr_name] = prop

        attrs['_properties'] = properties
        return type.__new__(cls, name, bases, attrs)


class DocumentSchema(object):
    __metaclass__ = SchemaProperties

    _dynamic_properties = None
    _allow_dynamic_properties = True
    _doc = None
    _db = None
    _doc_type_attr = 'doc_type'

    def __init__(self, _d=None, **properties):
        self._dynamic_properties = {}
        self._doc = {}

        if _d is not None:
            if not isinstance(_d, dict):
                raise TypeError('_d should be a dict')
            properties.update(_d)

        doc_type = getattr(self, '_doc_type', self.__class__.__name__)
        self._doc[self._doc_type_attr] = doc_type

        for prop in self._properties.values():
            if prop.name in properties:
                value = properties.pop(prop.name)
                if value is None:
                    value = prop.default_value()
            else:
                value = prop.default_value()
            prop.__property_init__(self, value)
            self.__dict__[prop.name] = value

        _dynamic_properties = properties.copy()
        for attr_name, value in _dynamic_properties.iteritems():
            if attr_name not in self._properties \
                    and value is not None:
                if isinstance(value, p.Property):
                    value.__property_config__(self, attr_name)
                    value.__property_init__(self, value.default_value())
                elif isinstance(value, DocumentSchema):
                    from couchdbkit.schema import SchemaProperty
                    value = SchemaProperty(value)
                    value.__property_config__(self, attr_name)
                    value.__property_init__(self, value.default_value())


                setattr(self, attr_name, value)
                # remove the kwargs to speed stuff
                del properties[attr_name]

    def dynamic_properties(self):
        """ get dict of dynamic properties """
        if self._dynamic_properties is None:
            return {}
        return self._dynamic_properties.copy()

    @classmethod
    def properties(cls):
        """ get dict of defined properties """
        return cls._properties.copy()

    def all_properties(self):
        """ get all properties.
        Generally we just need to use keys"""
        all_properties = self._properties.copy()
        all_properties.update(self.dynamic_properties())
        return all_properties

    def to_json(self):
        if self._doc.get(self._doc_type_attr) is None:
            doc_type = getattr(self, '_doc_type', self.__class__.__name__)
            self._doc[self._doc_type_attr] = doc_type
        return self._doc

    #TODO: add a way to maintain custom dynamic properties
    def __setattr__(self, key, value):
        """
        override __setattr__ . If value is in dir, we just use setattr.
        If value is not known (dynamic) we test if type and name of value
        is supported (in ALLOWED_PROPERTY_TYPES, Property instance and not
        start with '_') a,d add it to `_dynamic_properties` dict. If value is
        a list or a dict we use LazyList and LazyDict to maintain in the value.
        """

        if key == "_id" and valid_id(value):
            self._doc['_id'] = value
        elif key == "_deleted":
            self._doc["_deleted"] = value
        elif key == "_attachments":
            if key not in self._doc or not value:
                self._doc[key] = {}
            elif not isinstance(self._doc[key], dict):
                self._doc[key] = {}
            value = LazyDict(self._doc[key], init_vals=value)
        else:
            check_reserved_words(key)
            if not hasattr( self, key ) and not self._allow_dynamic_properties:
                raise AttributeError("%s is not defined in schema (not a valid property)" % key)

            elif not key.startswith('_') and \
                    key not in self.properties() and \
                    key not in dir(self):
                if type(value) not in ALLOWED_PROPERTY_TYPES and \
                        not isinstance(value, (p.Property,)):
                    raise TypeError("Document Schema cannot accept values of type '%s'." %
                            type(value).__name__)

                if self._dynamic_properties is None:
                    self._dynamic_properties = {}

                if isinstance(value, dict):
                    if key not in self._doc or not value:
                        self._doc[key] = {}
                    elif not isinstance(self._doc[key], dict):
                        self._doc[key] = {}
                    value = LazyDict(self._doc[key], init_vals=value)
                elif isinstance(value, list):
                    if key not in self._doc or not value:
                        self._doc[key] = []
                    elif not isinstance(self._doc[key], list):
                        self._doc[key] = []
                    value = LazyList(self._doc[key], init_vals=value)

                self._dynamic_properties[key] = value

                if not isinstance(value, (p.Property,)) and \
                        not isinstance(value, dict) and \
                        not isinstance(value, list):
                    if callable(value):
                        value = value()
                    self._doc[key] = convert_property(value)
            else:
                object.__setattr__(self, key, value)

    def __delattr__(self, key):
        """ delete property
        """
        if key in self._doc:
            del self._doc[key]

        if self._dynamic_properties and key in self._dynamic_properties:
            del self._dynamic_properties[key]
        else:
            object.__delattr__(self, key)

    def __getattr__(self, key):
        """ get property value
        """
        if self._dynamic_properties and key in self._dynamic_properties:
            return self._dynamic_properties[key]
        elif key  in ('_id', '_rev', '_attachments', 'doc_type'):
            return self._doc.get(key)
        try:
            return self.__dict__[key]
        except KeyError, e:
            raise AttributeError(e)

    def __getitem__(self, key):
        """ get property value
        """
        try:
            attr = getattr(self, key)
            if callable(attr):
                raise AttributeError("existing instance method")
            return attr
        except AttributeError:
            if key in self._doc:
                return self._doc[key]
            raise

    def __setitem__(self, key, value):
        """ add a property
        """
        setattr(self, key, value)


    def __delitem__(self, key):
        """ delete a property
        """
        try:
            delattr(self, key)
        except AttributeError, e:
            raise KeyError, e


    def __contains__(self, key):
        """ does object contain this propery ?

        @param key: name of property

        @return: True if key exist.
        """
        if key in self.all_properties():
            return True
        elif key in self._doc:
            return True
        return False

    def __iter__(self):
        """ iter document instance properties
        """
        for k in self.all_properties().keys():
            yield k, self[k]
        raise StopIteration

    iteritems = __iter__

    def items(self):
        """ return list of items
        """
        return [(k, self[k]) for k in self.all_properties().keys()]


    def __len__(self):
        """ get number of properties
        """
        return len(self._doc or ())

    def __getstate__(self):
        """ let pickle play with us """
        obj_dict = self.__dict__.copy()
        return obj_dict

    @classmethod
    def wrap(cls, data):
        """ wrap `data` dict in object properties """
        instance = cls()
        instance._doc = data
        for prop in instance._properties.values():
            if prop.name in data:
                value = data[prop.name]
                if value is not None:
                    value = prop.to_python(value)
                else:
                    value = prop.default_value()
            else:
                value = prop.default_value()
            prop.__property_init__(instance, value)

        if cls._allow_dynamic_properties:
            for attr_name, value in data.iteritems():
                if attr_name in instance.properties():
                    continue
                if value is None:
                    continue
                elif attr_name.startswith('_'):
                    continue
                elif attr_name == cls._doc_type_attr:
                    continue
                else:
                    value = value_to_python(value)
                    setattr(instance, attr_name, value)
        return instance
    from_json = wrap

    def validate(self, required=True):
        """ validate a document """
        for attr_name, value in self._doc.items():
            if attr_name in self._properties:
                self._properties[attr_name].validate(
                        getattr(self, attr_name), required=required)
        return True

    def clone(self, **kwargs):
        """ clone a document """
        kwargs.update(self._dynamic_properties)
        obj = self.__class__(**kwargs)
        obj._doc = self._doc
        return obj

    @classmethod
    def build(cls, **kwargs):
        """ build a new instance from this document object. """
        properties = {}
        for attr_name, attr in kwargs.items():
            if isinstance(attr, (p.Property,)):
                properties[attr_name] = attr
                attr.__property_config__(cls, attr_name)
            elif type(attr) in MAP_TYPES_PROPERTIES and \
                    not attr_name.startswith('_') and \
                    attr_name not in _NODOC_WORDS:
                check_reserved_words(attr_name)

                prop = MAP_TYPES_PROPERTIES[type(attr)](default=attr)
                properties[attr_name] = prop
                prop.__property_config__(cls, attr_name)
                properties[attr_name] = prop
        return type('AnonymousSchema', (cls,), properties)

class DocumentBase(DocumentSchema):
    """ Base Document object that map a CouchDB Document.
    It allow you to statically map a document by
    providing fields like you do with any ORM or
    dynamically. Ie unknown fields are loaded as
    object property that you can edit, datetime in
    iso3339 format are automatically translated in
    python types (date, time & datetime) and decimal too.

    Example of documentass

    .. code-block:: python

        from couchdbkit.schema import *
        class MyDocument(Document):
            mystring = StringProperty()
            myotherstring = unicode() # just use python types


    Document fields can be accessed as property or
    key of dict. These are similar : ``value = instance.key or value = instance['key'].``

    To delete a property simply do ``del instance[key'] or delattr(instance, key)``
    """
    _db = None

    def __init__(self, _d=None, **kwargs):
        _d = _d or {}

        docid = kwargs.pop('_id', _d.pop("_id", ""))
        docrev = kwargs.pop('_rev', _d.pop("_rev", ""))

        super(DocumentBase, self).__init__(_d, **kwargs)

        if docid: self._doc['_id'] = valid_id(docid)
        if docrev: self._doc['_rev'] = docrev

    @classmethod
    def set_db(cls, db):
        """ Set document db"""
        cls._db = db

    @classmethod
    def get_db(cls):
        """ get document db"""
        db = getattr(cls, '_db', None)
        if db is None:
            raise TypeError("doc database required to save document")
        return db

    def save(self, **params):
        """ Save document in database.

        @params db: couchdbkit.core.Database instance
        """
        self.validate()
        db = self.get_db()

        doc = self.to_json()
        db.save_doc(doc, **params)
        if '_id' in doc and '_rev' in doc:
            self._doc.update(doc)
        elif '_id' in doc:
            self._doc.update({'_id': doc['_id']})

    store = save

    @classmethod
    def save_docs(cls, docs, use_uuids=True, all_or_nothing=False):
        """ Save multiple documents in database.

        @params docs: list of couchdbkit.schema.Document instance
        @param use_uuids: add _id in doc who don't have it already set.
        @param all_or_nothing: In the case of a power failure, when the database
        restarts either all the changes will have been saved or none of them.
        However, it does not do conflict checking, so the documents will
        be committed even if this creates conflicts.

        """
        db = cls.get_db()
        docs_to_save= [doc for doc in docs if doc._doc_type == cls._doc_type]
        if not len(docs_to_save) == len(docs):
            raise ValueError("one of your documents does not have the correct type")
        db.bulk_save(docs_to_save, use_uuids=use_uuids, all_or_nothing=all_or_nothing)

    bulk_save = save_docs

    @classmethod
    def get(cls, docid, rev=None, db=None, dynamic_properties=True):
        """ get document with `docid`
        """
        if db is None:
            db = cls.get_db()
        cls._allow_dynamic_properties = dynamic_properties
        return db.get(docid, rev=rev, wrapper=cls.wrap)

    @classmethod
    def get_or_create(cls, docid=None, db=None, dynamic_properties=True, **params):
        """ get  or create document with `docid` """

        if db is not None:
            cls.set_db(db)
        cls._allow_dynamic_properties = dynamic_properties
        db = cls.get_db()

        if docid is None:
            obj = cls()
            obj.save(**params)
            return obj

        rev = params.pop('rev', None)

        try:
            return db.get(docid, rev=rev, wrapper=cls.wrap, **params)
        except ResourceNotFound:
            obj = cls()
            obj._id = docid
            obj.save(**params)
            return obj

    new_document = property(lambda self: self._doc.get('_rev') is None)

    def delete(self):
        """ Delete document from the database.
        @params db: couchdbkit.core.Database instance
        """
        if self.new_document:
            raise TypeError("the document is not saved")

        db = self.get_db()

        # delete doc
        db.delete_doc(self._id)

        # reinit document
        del self._doc['_id']
        del self._doc['_rev']

class AttachmentMixin(object):
    """
    mixin to manage doc attachments.

    """

    def put_attachment(self, content, name=None, content_type=None,
                content_length=None):
        """ Add attachement to a document.

        @param content: string or :obj:`File` object.
        @param name: name or attachment (file name).
        @param content_type: string, mimetype of attachment.
        If you don't set it, it will be autodetected.
        @param content_lenght: int, size of attachment.

        @return: bool, True if everything was ok.
        """
        db = self.get_db()
        return db.put_attachment(self._doc, content, name=name,
            content_type=content_type, content_length=content_length)

    def delete_attachment(self, name):
        """ delete document attachment

        @param name: name of attachment

        @return: dict, with member ok set to True if delete was ok.
        """

        db = self.get_db()
        result = db.delete_attachment(self._doc, name)
        try:
            self._doc['_attachments'].pop(name)
        except KeyError:
            pass
        return result

    def fetch_attachment(self, name, stream=False):
        """ get attachment in a adocument

        @param name: name of attachment default: default result
        @param stream: boolean, response return a ResponseStream object
        @param stream_size: int, size in bytes of response stream block

        @return: str or unicode, attachment
        """
        db = self.get_db()
        return db.fetch_attachment(self._doc, name, stream=stream)


class QueryMixin(object):
    """ Mixin that add query methods """

    @classmethod
    def view(cls, view_name, wrapper=None, dynamic_properties=None,
    wrap_doc=True, classes=None, **params):
        """ Get documents associated view a view.
        Results of view are automatically wrapped
        to Document object.

        @params view_name: str, name of view
        @params wrapper: override default wrapper by your own
        @dynamic_properties: do we handle properties which aren't in
        the schema ? Default is True.
        @wrap_doc: If True, if a doc is present in the row it will be
        used for wrapping. Default is True.
        @params params:  params of view

        @return: :class:`simplecouchdb.core.ViewResults` instance. All
        results are wrapped to current document instance.
        """
        db = cls.get_db()

        if not classes and not wrapper:
            classes = cls

        return db.view(view_name,
            dynamic_properties=dynamic_properties, wrap_doc=wrap_doc,
            wrapper=wrapper, schema=classes, **params)

    @classmethod
    def temp_view(cls, design, wrapper=None, dynamic_properties=None,
    wrap_doc=True, classes=None, **params):
        """ Slow view. Like in view method,
        results are automatically wrapped to
        Document object.

        @params design: design object, See `simplecouchd.client.Database`
        @dynamic_properties: do we handle properties which aren't in
            the schema ?
        @wrap_doc: If True, if a doc is present in the row it will be
            used for wrapping. Default is True.
        @params params:  params of view

        @return: Like view, return a :class:`simplecouchdb.core.ViewResults`
        instance. All results are wrapped to current document instance.
        """
        db = cls.get_db()
        return db.temp_view(design,
            dynamic_properties=dynamic_properties, wrap_doc=wrap_doc,
            wrapper=wrapper, schema=classes or cls, **params)

class Document(DocumentBase, QueryMixin, AttachmentMixin):
    """
    Full featured document object implementing the following :

    :class:`QueryMixin` for view & temp_view that wrap results to this object
    :class `AttachmentMixin` for attachments function
    """

class StaticDocument(Document):
    """
    Shorthand for a document that disallow dynamic properties.
    """
    _allow_dynamic_properties = False

########NEW FILE########
__FILENAME__ = properties
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

""" properties used by Document object """

import decimal
import datetime
import re
import time

try:
    from collections import MutableSet, Iterable

    def is_iterable(c):
        return isinstance(c, Iterable)

    support_setproperty = True
except ImportError:
    support_setproperty = False

from couchdbkit.exceptions import BadValueError

__all__ = ['ALLOWED_PROPERTY_TYPES', 'Property', 'StringProperty',
        'IntegerProperty', 'DecimalProperty', 'BooleanProperty',
        'FloatProperty', 'DateTimeProperty', 'DateProperty',
        'TimeProperty', 'DictProperty', 'StringDictProperty',
        'ListProperty', 'StringListProperty',
        'dict_to_json', 'list_to_json',
        'value_to_json', 'MAP_TYPES_PROPERTIES', 'value_to_python',
        'dict_to_python', 'list_to_python', 'convert_property',
        'value_to_property', 'LazyDict', 'LazyList']

if support_setproperty:
    __all__ += ['SetProperty', 'LazySet']

ALLOWED_PROPERTY_TYPES = set([
    basestring,
    str,
    unicode,
    bool,
    int,
    long,
    float,
    datetime.datetime,
    datetime.date,
    datetime.time,
    decimal.Decimal,
    dict,
    list,
    set,
    type(None)
])

re_date = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])$')
re_time = re.compile('^([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?$')
re_datetime = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])(\D?([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?([zZ]|([\+-])([01]\d|2[0-3])\D?([0-5]\d)?)?)?$')
re_decimal = re.compile('^(\d+)\.(\d+)$')

class Property(object):
    """ Property base which all other properties
    inherit."""
    creation_counter = 0

    def __init__(self, verbose_name=None, name=None,
            default=None, required=False, validators=None,
            choices=None):
        """ Default constructor for a property.

        :param verbose_name: str, verbose name of field, could
                be use for description
        :param name: str, name of field
        :param default: default value
        :param required: True if field is required, default is False
        :param validators: list of callable or callable, field validators
        function that are executed when document is saved.
        """
        self.verbose_name = verbose_name
        self.name = name
        self.default = default
        self.required = required
        self.validators = validators
        self.choices = choices
        self.creation_counter = Property.creation_counter
        Property.creation_counter += 1

    def __property_config__(self, document_class, property_name):
        self.document_class = document_class
        if self.name is None:
            self.name = property_name

    def __property_init__(self, document_instance, value):
        """ method used to set value of the property when
        we create the document. Don't check required. """
        if value is not None:
            value = self.to_json(self.validate(value, required=False))
        document_instance._doc[self.name] = value

    def __get__(self, document_instance, document_class):
        if document_instance is None:
            return self

        value = document_instance._doc.get(self.name)
        if value is not None:
            value = self._to_python(value)

        return value

    def __set__(self, document_instance, value):
        value = self.validate(value, required=False)
        document_instance._doc[self.name] = self._to_json(value)

    def __delete__(self, document_instance):
        pass

    def default_value(self):
        """ return default value """

        default = self.default
        if callable(default):
            default = default()
        return default

    def validate(self, value, required=True):
        """ validate value """
        if required and self.empty(value):
            if self.required:
                raise BadValueError("Property %s is required." % self.name)
        else:
            if self.choices and value is not None:
                if isinstance(self.choices, list):      choice_list = self.choices
                if isinstance(self.choices, dict):      choice_list = self.choices.keys()
                if isinstance(self.choices, tuple):     choice_list = [key for (key, name) in self.choices]

                if value not in choice_list:
                    raise BadValueError('Property %s is %r; must be one of %r' % (
                        self.name, value, choice_list))
        if self.validators:
            if isinstance(self.validators, (list, tuple,)):
                for validator in self.validators:
                    if callable(validator):
                        validator(value)
            elif callable(self.validators):
                self.validators(value)
        return value

    def empty(self, value):
        """ test if value is empty """
        return (not value and value != 0) or value is None

    def _to_python(self, value):
        if value == None:
            return value
        return self.to_python(value)

    def _to_json(self, value):
        if value == None:
            return value
        return self.to_json(value)

    def to_python(self, value):
        """ convert to python type """
        return unicode(value)

    def to_json(self, value):
        """ convert to json, Converted value is saved in couchdb. """
        return self.to_python(value)

    data_type = None

class StringProperty(Property):
    """ string property str or unicode property

    *Value type*: unicode
    """

    to_python = unicode

    def validate(self, value, required=True):
        value = super(StringProperty, self).validate(value,
                required=required)

        if value is None:
            return value

        if not isinstance(value, basestring):
            raise BadValueError(
                'Property %s must be unicode or str instance, not a %s' % (self.name, type(value).__name__))
        return value

    data_type = unicode

class IntegerProperty(Property):
    """ Integer property. map to int

    *Value type*: int
    """
    to_python = int

    def empty(self, value):
        return value is None

    def validate(self, value, required=True):
        value = super(IntegerProperty, self).validate(value,
                required=required)

        if value is None:
            return value

        if value is not None and not isinstance(value, (int, long,)):
            raise BadValueError(
                'Property %s must be %s or long instance, not a %s'
                % (self.name, type(self.data_type).__name__,
                    type(value).__name__))

        return value

    data_type = int
LongProperty = IntegerProperty

class FloatProperty(Property):
    """ Float property, map to python float

    *Value type*: float
    """
    to_python = float
    data_type = float

    def validate(self, value, required=True):
        value = super(FloatProperty, self).validate(value,
                required=required)

        if value is None:
            return value

        if not isinstance(value, float):
            raise BadValueError(
                'Property %s must be float instance, not a %s'
                % (self.name, type(value).__name__))

        return value
Number = FloatProperty

class BooleanProperty(Property):
    """ Boolean property, map to python bool

    *ValueType*: bool
    """
    to_python = bool
    data_type = bool

    def validate(self, value, required=True):
        value = super(BooleanProperty, self).validate(value,
                required=required)

        if value is None:
            return value

        if value is not None and not isinstance(value, bool):
            raise BadValueError(
                'Property %s must be bool instance, not a %s'
                % (self.name, type(value).__name__))

        return value

    def empty(self, value):
        """test if boolean is empty"""
        return value is None

class DecimalProperty(Property):
    """ Decimal property, map to Decimal python object

    *ValueType*: decimal.Decimal
    """
    data_type = decimal.Decimal

    def to_python(self, value):
        return decimal.Decimal(value)

    def to_json(self, value):
        return unicode(value)

class DateTimeProperty(Property):
    """DateTime property. It convert iso3339 string
    to python and vice-versa. Map to datetime.datetime
    object.

    *ValueType*: datetime.datetime
    """

    def __init__(self, verbose_name=None, auto_now=False, auto_now_add=False,
               **kwds):
        super(DateTimeProperty, self).__init__(verbose_name, **kwds)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

    def validate(self, value, required=True):
        value = super(DateTimeProperty, self).validate(value, required=required)

        if value is None:
            return value

        if value and not isinstance(value, self.data_type):
            raise BadValueError('Property %s must be a %s, current is %s' %
                          (self.name, self.data_type.__name__, type(value).__name__))
        return value

    def default_value(self):
        if self.auto_now or self.auto_now_add:
            return self.now()
        return Property.default_value(self)

    def to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = value.split('.', 1)[0] # strip out microseconds
                value = value[0:19] # remove timezone
                value = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
            except ValueError, e:
                raise ValueError('Invalid ISO date/time %r [%s]' %
                        (value, str(e)))
        return value

    def to_json(self, value):
        if self.auto_now:
            value = self.now()

        if value is None:
            return value
        return value.replace(microsecond=0).isoformat() + 'Z'

    data_type = datetime.datetime

    @staticmethod
    def now():
        return datetime.datetime.utcnow()

class DateProperty(DateTimeProperty):
    """ Date property, like DateTime property but only
    for Date. Map to datetime.date object

    *ValueType*: datetime.date
    """
    data_type = datetime.date

    @staticmethod
    def now():
        return datetime.datetime.now().date()

    def to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = datetime.date(*time.strptime(value, '%Y-%m-%d')[:3])
            except ValueError, e:
                raise ValueError('Invalid ISO date %r [%s]' % (value,
                    str(e)))
        return value

    def to_json(self, value):
        if value is None:
            return value
        return value.isoformat()

class TimeProperty(DateTimeProperty):
    """ Date property, like DateTime property but only
    for time. Map to datetime.time object

    *ValueType*: datetime.time
    """

    data_type = datetime.time

    @staticmethod
    def now(self):
        return datetime.datetime.now().time()

    def to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = value.split('.', 1)[0] # strip out microseconds
                value = datetime.time(*time.strptime(value, '%H:%M:%S')[3:6])
            except ValueError, e:
                raise ValueError('Invalid ISO time %r [%s]' % (value,
                    str(e)))
        return value

    def to_json(self, value):
        if value is None:
            return value
        return value.replace(microsecond=0).isoformat()


class DictProperty(Property):
    """ A property that stores a dict of things"""

    def __init__(self, verbose_name=None, default=None,
        required=False, **kwds):
        """
        :args verbose_name: Optional verbose name.
        :args default: Optional default value; if omitted, an empty list is used.
        :args**kwds: Optional additional keyword arguments, passed to base class.

        Note that the only permissible value for 'required' is True.
        """

        if default is None:
            default = {}

        Property.__init__(self, verbose_name, default=default,
            required=required, **kwds)

    data_type = dict

    def validate(self, value, required=True):
        value = super(DictProperty, self).validate(value, required=required)
        if value and value is not None:
            if not isinstance(value, dict):
                raise BadValueError('Property %s must be a dict' % self.name)
            value = self.validate_dict_contents(value)
        return value

    def validate_dict_contents(self, value):
        try:
            value = validate_dict_content(value)
        except BadValueError:
            raise BadValueError(
                'Items of %s dict must all be in %s' %
                    (self.name, ALLOWED_PROPERTY_TYPES))
        return value

    def default_value(self):
        """Default value for list.

        Because the property supplied to 'default' is a static value,
        that value must be shallow copied to prevent all fields with
        default values from sharing the same instance.

        Returns:
          Copy of the default value.
        """
        value = super(DictProperty, self).default_value()
        if value is None:
            value = {}
        return dict(value)

    def to_python(self, value):
        return LazyDict(value)

    def to_json(self, value):
        return value_to_json(value)



class StringDictProperty(DictProperty):

    def to_python(self, value):
        return LazyDict(value, item_type=basestring)

    def validate_dict_contents(self, value):
        try:
            value = validate_dict_content(value, basestring)
        except BadValueError:
            raise BadValueError(
                'Items of %s dict must all be in %s' %
                    (self.name, basestring))
        return value



class ListProperty(Property):
    """A property that stores a list of things.

      """
    def __init__(self, verbose_name=None, default=None,
            required=False, item_type=None, **kwds):
        """Construct ListProperty.


         :args verbose_name: Optional verbose name.
         :args default: Optional default value; if omitted, an empty list is used.
         :args**kwds: Optional additional keyword arguments, passed to base class.


        """
        if default is None:
            default = []

        if item_type is not None and item_type not in ALLOWED_PROPERTY_TYPES:
            raise ValueError('item_type %s not in %s' % (item_type, ALLOWED_PROPERTY_TYPES))
        self.item_type = item_type

        Property.__init__(self, verbose_name, default=default,
            required=required, **kwds)

    data_type = list

    def validate(self, value, required=True):
        value = super(ListProperty, self).validate(value, required=required)
        if value and value is not None:
            if not isinstance(value, list):
                raise BadValueError('Property %s must be a list' % self.name)
            value = self.validate_list_contents(value)
        return value

    def validate_list_contents(self, value):
        value = validate_list_content(value, item_type=self.item_type)
        try:
            value = validate_list_content(value, item_type=self.item_type)
        except BadValueError:
            raise BadValueError(
                'Items of %s list must all be in %s' %
                    (self.name, ALLOWED_PROPERTY_TYPES))
        return value

    def default_value(self):
        """Default value for list.

        Because the property supplied to 'default' is a static value,
        that value must be shallow copied to prevent all fields with
        default values from sharing the same instance.

        Returns:
          Copy of the default value.
        """
        value = super(ListProperty, self).default_value()
        if value is None:
            value = []
        return list(value)

    def to_python(self, value):
        return LazyList(value, item_type=self.item_type)

    def to_json(self, value):
        return value_to_json(value, item_type=self.item_type)


class StringListProperty(ListProperty):
    """ shorthand for list that should containe only unicode"""

    def __init__(self, verbose_name=None, default=None,
            required=False, **kwds):
        super(StringListProperty, self).__init__(verbose_name=verbose_name,
            default=default, required=required, item_type=basestring, **kwds)





#  dict proxy

class LazyDict(dict):
    """ object to make sure we keep updated of dict
    in _doc. We just override a dict and maintain change in
    doc reference (doc[keyt] obviously).

    if init_vals is specified, doc is overwritten
    with the dict given. Otherwise, the values already in
    doc are used.
    """

    def __init__(self, doc, item_type=None, init_vals=None):
        dict.__init__(self)
        self.item_type = item_type

        self.doc = doc
        if init_vals is None:
            self._wrap()
        else:
            for key, value in init_vals.items():
                self[key] = value

    def _wrap(self):
        for key, json_value in self.doc.items():
            if isinstance(json_value, dict):
                value = LazyDict(json_value, item_type=self.item_type)
            elif isinstance(json_value, list):
                value = LazyList(json_value, item_type=self.item_type)
            else:
                value = value_to_python(json_value, self.item_type)
            dict.__setitem__(self, key, value)

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            self.doc[key] = {}
            value = LazyDict(self.doc[key], item_type=self.item_type, init_vals=value)
        elif isinstance(value, list):
            self.doc[key] = []
            value = LazyList(self.doc[key], item_type=self.item_type, init_vals=value)
        else:
            self.doc.update({key: value_to_json(value, item_type=self.item_type) })
        super(LazyDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        del self.doc[key]
        super(LazyDict, self).__delitem__(key)

    def pop(self, key, *args):
        default = len(args) == 1
        if default:
            self.doc.pop(key, args[-1])
            return super(LazyDict, self).pop(key, args[-1])
        self.doc.pop(key)
        return super(LazyDict, self).pop(key)

    def setdefault(self, key, default):
        if key in self:
            return self[key]
        self.doc.setdefault(key, value_to_json(default, item_type=self.item_type))
        super(LazyDict, self).setdefault(key, default)
        return default

    def update(self, value):
        for k, v in value.items():
            self[k] = v

    def popitem(self, value):
        new_value = super(LazyDict, self).popitem(value)
        self.doc.popitem(value_to_json(value, item_type=self.item_type))
        return new_value

    def clear(self):
        self.doc.clear()
        super(LazyDict, self).clear()


class LazyList(list):
    """ object to make sure we keep update of list
    in _doc. We just override a list and maintain change in
    doc reference (doc[index] obviously).

    if init_vals is specified, doc is overwritten
    with the list given. Otherwise, the values already in
    doc are used.
    """

    def __init__(self, doc, item_type=None, init_vals=None):
        list.__init__(self)

        self.item_type = item_type
        self.doc = doc
        if init_vals is None:
            # just wrap the current values
            self._wrap()
        else:
            # initialize this list and the underlying list
            # with the values given.
            del self.doc[:]
            for item in init_vals:
                self.append(item)

    def _wrap(self):
        for json_value in self.doc:
            if isinstance(json_value, dict):
                value = LazyDict(json_value, item_type=self.item_type)
            elif isinstance(json_value, list):
                value = LazyList(json_value, item_type=self.item_type)
            else:
                value = value_to_python(json_value, self.item_type)
            list.append(self, value)

    def __delitem__(self, index):
        del self.doc[index]
        list.__delitem__(self, index)

    def __setitem__(self, index, value):
        if isinstance(value, dict):
            self.doc[index] = {}
            value = LazyDict(self.doc[index], item_type=self.item_type, init_vals=value)
        elif isinstance(value, list):
            self.doc[index] = []
            value = LazyList(self.doc[index], item_type=self.item_type, init_vals=value)
        else:
            self.doc[index] = value_to_json(value, item_type=self.item_type)
        list.__setitem__(self, index, value)


    def __delslice__(self, i, j):
        del self.doc[i:j]
        list.__delslice__(self, i, j)

    def __getslice__(self, i, j):
        return LazyList(self.doc[i:j], self.item_type)

    def __setslice__(self, i, j, seq):
        self.doc[i:j] = (value_to_json(v, item_type=self.item_type) for v in seq)
        list.__setslice__(self, i, j, seq)

    def __contains__(self, value):
        jvalue = value_to_json(value)
        for m in self.doc:
            if m == jvalue: return True
        return False

    def append(self, *args, **kwargs):
        if args:
            assert len(args) == 1
            value = args[0]
        else:
            value = kwargs

        index = len(self)
        if isinstance(value, dict):
            self.doc.append({})
            value = LazyDict(self.doc[index], item_type=self.item_type, init_vals=value)
        elif isinstance(value, list):
            self.doc.append([])
            value = LazyList(self.doc[index], item_type=self.item_type, init_vals=value)
        else:
            self.doc.append(value_to_json(value, item_type=self.item_type))
        super(LazyList, self).append(value)

    def extend(self, x):
        self.doc.extend(
            [value_to_json(v, item_type=self.item_type) for v in x])
        super(LazyList, self).extend(x)

    def index(self, x, *args):
        x = value_to_json(x, item_type=self.item_type)
        return self.doc.index(x)

    def insert(self, i, x):
        self.__setslice__(i, i, [x])

    def pop(self, i=-1):
        del self.doc[i]
        v = super(LazyList, self).pop(i)
        return value_to_python(v, item_type=self.item_type)

    def remove(self, x):
        del self[self.index(x)]

    def sort(self, cmp=None, key=None, reverse=False):
        self.doc.sort(cmp, key, reverse)
        list.sort(self, cmp, key, reverse)

    def reverse(self):
        self.doc.reverse()
        list.reverse(self)

if support_setproperty:
    class SetProperty(Property):
        """A property that stores a Python set as a list of unique
        elements.

        Note that Python set operations like union that return a set
        object do not alter list that will be stored with the next save,
        while operations like update that change a set object in-place do
        keep the list in sync.
        """
        def __init__(self, verbose_name=None, default=None, required=None,
                     item_type=None, **kwds):
            """Construct SetProperty.

             :args verbose_name: Optional verbose name.

             :args default: Optional default value; if omitted, an empty
                            set is used.

             :args required: True if field is required, default is False.

             :args item_type: Optional data type of items that set
                              contains.  Used to assist with JSON
                              serialization/deserialization when data is
                              stored/retireved.

             :args **kwds: Optional additional keyword arguments, passed to
                           base class.
             """
            if default is None:
                default = set()
            if item_type is not None and item_type not in ALLOWED_PROPERTY_TYPES:
                raise ValueError('item_type %s not in %s'
                                 % (item_type, ALLOWED_PROPERTY_TYPES))
            self.item_type = item_type
            super(SetProperty, self).__init__(
                verbose_name=verbose_name, default=default, required=required,
                **kwds)

        data_type = set

        def validate(self, value, required=True):
            value = super(SetProperty, self).validate(value, required=required)
            if value and value is not None:
                if not isinstance(value, MutableSet):
                    raise BadValueError('Property %s must be a set' % self.name)
                value = self.validate_set_contents(value)
            return value

        def validate_set_contents(self, value):
            try:
                value = validate_set_content(value, item_type=self.item_type)
            except BadValueError:
                raise BadValueError(
                    'Items of %s set must all be in %s' %
                        (self.name, ALLOWED_PROPERTY_TYPES))
            return value

        def default_value(self):
            """Return default value for set.

            Because the property supplied to 'default' is a static value,
            that value must be shallow copied to prevent all fields with
            default values from sharing the same instance.

            Returns:
              Copy of the default value.
            """
            value = super(SetProperty, self).default_value()
            if value is None:
                return set()
            return value.copy()

        def to_python(self, value):
            return LazySet(value, item_type=self.item_type)

        def to_json(self, value):
            return value_to_json(value, item_type=self.item_type)


    class LazySet(MutableSet):
        """Object to make sure that we keep set and _doc synchronized.

        We sub-class MutableSet and maintain changes in doc.

        Note that methods like union that return a set object do not
        alter _doc, while methods like update that change a set object
        in-place do keep _doc in sync.
        """
        def _map_named_operation(opname):
            fn = getattr(MutableSet, opname)
            if hasattr(fn, 'im_func'):
                fn = fn.im_func
            def method(self, other, fn=fn):
                if not isinstance(other, MutableSet):
                    other = self._from_iterable(other)
                return fn(self, other)
            return method

        issubset = _map_named_operation('__le__')
        issuperset = _map_named_operation('__ge__')
        symmetric_difference = _map_named_operation('__xor__')

        def __init__(self, doc, item_type=None):
            self.item_type = item_type
            self.doc = doc
            self.elements = set(value_to_python(value, self.item_type)
                                for value in self.doc)

        def __repr__(self):
            return '%s(%r)' % (type(self).__name__, list(self))

        @classmethod
        def _from_iterable(cls, it):
            return cls(it)

        def __iand__(self, iterator):
            for value in (self.elements - iterator):
                self.elements.discard(value)
            return self

        def __iter__(self):
            return iter(element for element in self.elements)

        def __len__(self):
            return len(self.elements)

        def __contains__(self, item):
            return item in self.elements

        def __xor__(self, other):
            if not isinstance(other, MutableSet):
                if not is_iterable(other):
                    return NotImplemented
                other = self._from_iterable(other)
            return (self.elements - other) | (other - self.elements)

        def __gt__(self, other):
            if not isinstance(other, MutableSet):
                return NotImplemented
            return other < self.elements

        def __ge__(self, other):
            if not isinstance(other, MutableSet):
                return NotImplemented
            return other <= self.elements

        def __ne__(self, other):
            return not (self.elements == other)

        def add(self, value):
            self.elements.add(value)
            if value not in self.doc:
                self.doc.append(value_to_json(value, item_type=self.item_type))

        def copy(self):
            return self.elements.copy()

        def difference(self, other, *args):
            return self.elements.difference(other, *args)

        def difference_update(self, other, *args):
            for value in other:
                self.discard(value)
            for arg in args:
                self.difference_update(arg)

        def discard(self, value):
            self.elements.discard(value)
            try:
                self.doc.remove(value)
            except ValueError:
                pass

        def intersection(self, other, *args):
            return self.elements.intersection(other, *args)

        def intersection_update(self, other, *args):
            if not isinstance(other, MutableSet):
                other = set(other)
            for value in self.elements - other:
                self.discard(value)
            for arg in args:
                self.intersection_update(arg)

        def symmetric_difference_update(self, other):
            if not isinstance(other, MutableSet):
                other = set(other)
            for value in other:
                if value in self.elements:
                    self.discard(value)
                else:
                    self.add(value)

        def union(self, other, *args):
            return self.elements.union(other, *args)

        def update(self, other, *args):
            self.elements.update(other, *args)
            for element in self.elements:
                if element not in self.doc:
                    self.doc.append(
                        value_to_json(element, item_type=self.item_type))

# some mapping

MAP_TYPES_PROPERTIES = {
        decimal.Decimal: DecimalProperty,
        datetime.datetime: DateTimeProperty,
        datetime.date: DateProperty,
        datetime.time: TimeProperty,
        str: StringProperty,
        unicode: StringProperty,
        bool: BooleanProperty,
        int: IntegerProperty,
        long: LongProperty,
        float: FloatProperty,
        list: ListProperty,
        dict: DictProperty
}

if support_setproperty:
    MAP_TYPES_PROPERTIES[set] = SetProperty

def convert_property(value):
    """ convert a value to json from Property._to_json """
    if type(value) in MAP_TYPES_PROPERTIES:
        prop = MAP_TYPES_PROPERTIES[type(value)]()
        value = prop.to_json(value)
    return value


def value_to_property(value):
    """ Convert value in a Property object """
    if type(value) in MAP_TYPES_PROPERTIES:
        prop = MAP_TYPES_PROPERTIES[type(value)]()
        return prop
    else:
        return value

# utilities functions

def validate_list_content(value, item_type=None):
    """ validate type of values in a list """
    return [validate_content(item, item_type=item_type) for item in value]

def validate_dict_content(value, item_type=None):
    """ validate type of values in a dict """
    return dict([(k, validate_content(v,
                item_type=item_type)) for k, v in value.iteritems()])

def validate_set_content(value, item_type=None):
    """ validate type of values in a set """
    return set(validate_content(item, item_type=item_type) for item in value)

def validate_content(value, item_type=None):
    """ validate a value. test if value is in supported types """
    if isinstance(value, list):
        value = validate_list_content(value, item_type=item_type)
    elif isinstance(value, dict):
        value = validate_dict_content(value, item_type=item_type)
    elif item_type is not None and not isinstance(value, item_type):
        raise BadValueError(
            'Items  must all be in %s' % item_type)
    elif type(value) not in ALLOWED_PROPERTY_TYPES:
            raise BadValueError(
                'Items  must all be in %s' %
                    (ALLOWED_PROPERTY_TYPES))
    return value

def dict_to_json(value, item_type=None):
    """ convert a dict to json """
    return dict([(k, value_to_json(v, item_type=item_type)) for k, v in value.iteritems()])

def list_to_json(value, item_type=None):
    """ convert a list to json """
    return [value_to_json(item, item_type=item_type) for item in value]

def value_to_json(value, item_type=None):
    """ convert a value to json using appropriate regexp.
    For Dates we use ISO 8601. Decimal are converted to string.

    """
    if isinstance(value, datetime.datetime) and is_type_ok(item_type, datetime.datetime):
        value = value.replace(microsecond=0).isoformat() + 'Z'
    elif isinstance(value, datetime.date) and is_type_ok(item_type, datetime.date):
        value = value.isoformat()
    elif isinstance(value, datetime.time) and is_type_ok(item_type, datetime.time):
        value = value.replace(microsecond=0).isoformat()
    elif isinstance(value, decimal.Decimal) and is_type_ok(item_type, decimal.Decimal):
        value = unicode(value)
    elif isinstance(value, (list, MutableSet)):
        value = list_to_json(value, item_type)
    elif isinstance(value, dict):
        value = dict_to_json(value, item_type)
    return value

def is_type_ok(item_type, value_type):
    return item_type is None or item_type == value_type


def value_to_python(value, item_type=None):
    """ convert a json value to python type using regexp. values converted
    have been put in json via `value_to_json` .
    """
    data_type = None
    if isinstance(value, basestring):
        if re_date.match(value) and is_type_ok(item_type, datetime.date):
            data_type = datetime.date
        elif re_time.match(value) and is_type_ok(item_type, datetime.time):
            data_type = datetime.time
        elif re_datetime.match(value) and is_type_ok(item_type, datetime.datetime):
            data_type = datetime.datetime
        elif re_decimal.match(value) and is_type_ok(item_type, decimal.Decimal):
            data_type = decimal.Decimal
        if data_type is not None:
            prop = MAP_TYPES_PROPERTIES[data_type]()
            try:
                #sometimes regex fail so return value
                value = prop.to_python(value)
            except:
                pass
    elif isinstance(value, (list, MutableSet)):
        value = list_to_python(value, item_type=item_type)
    elif isinstance(value, dict):
        value = dict_to_python(value, item_type=item_type)
    return value

def list_to_python(value, item_type=None):
    """ convert a list of json values to python list """
    return [value_to_python(item, item_type=item_type) for item in value]

def dict_to_python(value, item_type=None):
    """ convert a json object values to python dict """
    return dict([(k, value_to_python(v, item_type=item_type)) for k, v in value.iteritems()])

########NEW FILE########
__FILENAME__ = properties_proxy
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

""" Meta properties """

from ..exceptions import BadValueError

from .base import DocumentSchema
from .properties import Property

__all__ = ['SchemaProperty', 'SchemaListProperty', 'SchemaDictProperty']

class SchemaProperty(Property):
    """ Schema property. It allows you add a DocumentSchema instance 
    a member of a Document object. It returns a
   `schemaDocumentSchema` object.

    Exemple :
    
            >>> from couchdbkit import *
            >>> class Blog(DocumentSchema):
            ...     title = StringProperty()
            ...     author = StringProperty(default="me")
            ... 
            >>> class Entry(Document):
            ...     title = StringProperty()
            ...     body = StringProperty()
            ...     blog = SchemaProperty(Blog())
            ... 
            >>> test = Entry()
            >>> test._doc
            {'body': None, 'doc_type': 'Entry', 'title': None, 'blog': {'doc_type': 'Blog', 'author': u'me', 'title': None}}
            >>> test.blog.title = "Mon Blog"
            >>> test._doc
            {'body': None, 'doc_type': 'Entry', 'title': None, 'blog': {'doc_type': 'Blog', 'author': u'me', 'title': u'Mon Blog'}}
            >>> test.blog.title
            u'Mon Blog'
            >>> from couchdbkit import Server
            >>> s = Server()
            >>> db = s.create_db('couchdbkit_test')
            >>> Entry._db = db 
            >>> test.save()
            >>> doc = Entry.objects.get(test.id)
            >>> doc.blog.title
            u'Mon Blog'
            >>> del s['simplecouchdb_test']

    """

    def __init__(self, schema, verbose_name=None, name=None, 
            required=False, validators=None, default=None):

        Property.__init__(self, verbose_name=None,
            name=None, required=False, validators=None, default=default)
       
        use_instance = True
        if isinstance(schema, type):
            use_instance = False    

        elif not isinstance(schema, DocumentSchema):
            raise TypeError('schema should be a DocumentSchema instance')
       
        elif schema.__class__.__name__ == 'DocumentSchema':
            use_instance = False
            properties = schema._dynamic_properties.copy()
            schema = DocumentSchema.build(**properties)
            
        self._use_instance = use_instance
        self._schema = schema

    def default_value(self):
        if not self._use_instance:
            if self.default:
                return self.default
            return self._schema()
        return self._schema.clone()

    def empty(self, value):
        if not hasattr(value, '_doc'):
            return True
        if not value._doc or value._doc is None:
            return True
        return False

    def validate(self, value, required=True):
        value.validate(required=required)
        value = super(SchemaProperty, self).validate(value)

        if value is None:
            return value

        if not isinstance(value, DocumentSchema):
            raise BadValueError(
                'Property %s must be DocumentSchema instance, not a %s' % (self.name, 
                type(value).__name__))
        return value

    def to_python(self, value):
        if not self._use_instance:
            schema = self._schema
        else:
            schema = self._schema.__class__
        return schema.wrap(value)

    def to_json(self, value):
        if not isinstance(value, DocumentSchema):
            if not self._use_instance:
                schema = self._schema()
            else:
                schema = self._schema.clone()

            if not isinstance(value, dict):
                raise BadValueError("%s is not a dict" % str(value))
            value = schema(**value)

        return value._doc

class SchemaListProperty(Property):
    """A property that stores a list of things.

      """
    def __init__(self, schema, verbose_name=None, default=None, 
            required=False, **kwds):
        
        Property.__init__(self, verbose_name, default=default,
            required=required, **kwds)
    
        use_instance = True
        if isinstance(schema, type):
            use_instance = False    

        elif not isinstance(schema, DocumentSchema):
            raise TypeError('schema should be a DocumentSchema instance')
       
        elif schema.__class__.__name__ == 'DocumentSchema':
            use_instance = False
            properties = schema._dynamic_properties.copy()
            schema = DocumentSchema.build(**properties)
            
        self._use_instance = use_instance
        self._schema = schema
        
    def validate(self, value, required=True):
        value = super(SchemaListProperty, self).validate(value, required=required)
        if value and value is not None:
            if not isinstance(value, list):
                raise BadValueError('Property %s must be a list' % self.name)
            value = self.validate_list_schema(value, required=required)
        return value
        
    def validate_list_schema(self, value, required=True):
        for v in value:
            v.validate(required=required)
        return value
        
    def default_value(self):
        return []
        
    def to_python(self, value):
        return LazySchemaList(value, self._schema, self._use_instance)
        
    def to_json(self, value):
        return [svalue_to_json(v, self._schema, self._use_instance) for v in value]
        
        
class LazySchemaList(list):

    def __init__(self, doc, schema, use_instance, init_vals=None):
        list.__init__(self)
        
        self.schema = schema
        self.use_instance = use_instance
        self.doc = doc
        if init_vals is None:
            # just wrap the current values
            self._wrap()
        else:
            # initialize this list and the underlying list
            # with the values given.
            del self.doc[:]
            for item in init_vals:
                self.append(item)

    def _wrap(self):
        for v in self.doc:
            if not self.use_instance: 
                schema = self.schema()
            else:
                schema = self.schema.clone()
                
            value = schema.wrap(v)
            list.append(self, value)

    def __delitem__(self, index):
        del self.doc[index]
        list.__delitem__(self, index)

    def __setitem__(self, index, value):
        self.doc[index] = svalue_to_json(value, self.schema, 
                                    self.use_instance)
        list.__setitem__(self, index, value)

    def __delslice__(self, i, j):
        del self.doc[i:j]
        super(LazySchemaList, self).__delslice__(i, j)

    def __getslice__(self, i, j):
        return LazySchemaList(self.doc[i:j], self.schema, self.use_instance)

    def __setslice__(self, i, j, seq):
        self.doc[i:j] = (svalue_to_json(v, self.schema, self.use_instance)
                         for v in seq)
        super(LazySchemaList, self).__setslice__(i, j, seq)

    def __contains__(self, value):
        for item in self.doc:
            if item == value._doc:
                return True
        return False

    def append(self, *args, **kwargs):
        if args:
            assert len(args) == 1
            value = args[0]
        else:
            value = kwargs

        self.doc.append(svalue_to_json(value, self.schema, 
                                    self.use_instance))
        super(LazySchemaList, self).append(value)

    def count(self, value):
        return sum(1 for item in self.doc if item == value._doc)

    def extend(self, x):
        self.doc.extend([svalue_to_json(item, self.schema, self.use_instance)
                         for item in x])
        super(LazySchemaList, self).extend(x)

    def index(self, value, *args):
        try:
            i = max(0, args[0])
        except IndexError:
            i = 0
        try:
            j = min(len(self.doc), args[1])
        except IndexError:
            j = len(self.doc)
        if j < 0:
            j += len(self.doc)
        for idx, item in enumerate(self.doc[i:j]):
            if item == value._doc:
                return idx + i
        else:
            raise ValueError('list.index(x): x not in list')

    def insert(self, index, value):
        self.__setslice__(index, index, [value])

    def pop(self, index=-1):
        del self.doc[index]
        return super(LazySchemaList, self).pop(index)

    def remove(self, value):
        try:
            del self[self.index(value)]
        except ValueError:
            raise ValueError('list.remove(x): x not in list')

    def reverse(self):
        self.doc.reverse()
        list.reverse(self)

    def sort(self, cmp=None, key=None, reverse=False):
        self.doc.sort(cmp, key, reverse)
        list.sort(self, cmp, key, reverse)
        
        
class SchemaDictProperty(Property):
    """A property that stores a dict of things.

      """
    def __init__(self, schema, verbose_name=None, default=None,
            required=False, **kwds):

        Property.__init__(self, verbose_name, default=default,
            required=required, **kwds)

        use_instance = True
        if isinstance(schema, type):
            use_instance = False

        elif not isinstance(schema, DocumentSchema):
            raise TypeError('schema should be a DocumentSchema instance')

        elif schema.__class__.__name__ == 'DocumentSchema':
            use_instance = False
            properties = schema._dynamic_properties.copy()
            schema = DocumentSchema.build(**properties)

        self._use_instance = use_instance
        self._schema = schema

    def validate(self, value, required=True):
        value = super(SchemaDictProperty, self).validate(value, required=required)
        if value and value is not None:
            if not isinstance(value, dict):
                raise BadValueError('Property %s must be a dict' % self.name)
            value = self.validate_dict_schema(value, required=required)
        return value

    def validate_dict_schema(self, value, required=True):
        for v in value.values():
             v.validate(required=required)
        return value

    def default_value(self):
        return {}

    def to_python(self, value):
        return LazySchemaDict(value, self._schema, self._use_instance)

    def to_json(self, value):
        return dict([(k, svalue_to_json(v, self._schema, self._use_instance)) for k, v in value.items()])


class LazySchemaDict(dict):

    def __init__(self, doc, schema, use_instance, init_vals=None):
        dict.__init__(self)

        self.schema = schema
        self.use_instance = use_instance
        self.doc = doc
        if init_vals is None:
            # just wrap the current values
            self._wrap()
        else:
            # initialize this dict and the underlying dict
            # with the values given.
            del self.doc[:]
            for k, v in init_vals:
                self[k] = self._wrap(v)

    def _wrap(self):
        for k, v in self.doc.items():
            if not self.use_instance:
                schema = self.schema()
            else:
                schema = self.schema.clone()

            value = schema.wrap(v)
            dict.__setitem__(self, k, value)

    def __delitem__(self, index):
        index = str(index)
        del self.doc[index]
        dict.__delitem__(self, index)

    def __getitem__(self, index):
        index = str(index)
        return dict.__getitem__(self, index)

    def __setitem__(self, index, value):
        index = str(index)
        self.doc[index] = svalue_to_json(value, self.schema,
                                    self.use_instance)
        dict.__setitem__(self, index, value)

        
def svalue_to_json(value, schema, use_instance):
    if not isinstance(value, DocumentSchema):
        if not isinstance(value, dict):
            raise BadValueError("%s is not a dict" % str(value))

        if not use_instance:
            value = schema(**value)
        else:
            value = schema.clone(**value)

    return value._doc

########NEW FILE########
__FILENAME__ = util
from couchdbkit.exceptions import DocTypeError


def schema_map(schema, dynamic_properties):
    if hasattr(schema, "wrap") and hasattr(schema, '_doc_type'):
        schema = {schema._doc_type: schema}
    elif isinstance(schema, list):
        schema = dict((s._doc_type, s) for s in schema)

    if dynamic_properties is not None:
        for name, cls in schema.items():
            if cls._allow_dynamic_properties != dynamic_properties:
                schema[name] = type(cls.__name__, (cls,), {
                    '_allow_dynamic_properties': dynamic_properties,
                })
    return schema


def doctype_attr_of(classes):
    doc_type_attrs = set(cls._doc_type_attr for cls in classes)
    assert len(doc_type_attrs) == 1, "inconsistent doctype attr"
    return doc_type_attrs.pop()


def get_multi_wrapper(classes):
    doctype_attr = doctype_attr_of(classes.values())

    def wrap(doc):
        doc_type = doc.get(doctype_attr)
        try:
            cls = classes[doc_type]
        except KeyError:
            raise DocTypeError(
                "the document being wrapped has doc type {0!r}. "
                "To wrap it anyway, you must explicitly pass in "
                "classes={{{0!r}: <document class>}} to your view. "
                "This behavior is new starting in 0.6.2.".format(doc_type)
            )
        return cls.wrap(doc)

    return wrap


def schema_wrapper(schema, dynamic_properties=None):
    if hasattr(schema, "wrap") and hasattr(schema, '_doc_type') and not dynamic_properties:
        return schema.wrap
    mapping = schema_map(schema, dynamic_properties)
    return get_multi_wrapper(mapping)


def maybe_schema_wrapper(schema, params):
    dynamic_properties = params.pop('dynamic_properties', None)
    return schema_wrapper(schema, dynamic_properties)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.


"""
Mostly utility functions couchdbkit uses internally that don't
really belong anywhere else in the modules.
"""
from __future__ import with_statement

import codecs
import string
from hashlib import md5
import os
import re
import sys
import urllib


try:
    import ujson as json

except ImportError:

    try:
        import simplejson as json
    except ImportError:
        try:
            import json
        except ImportError:
            raise ImportError("""simplejson isn't installed

    Install it with the command:

        pip install simplejson
    """)


# backport relpath from python2.6
if not hasattr(os.path, 'relpath'):
    if os.name == "nt":
        def splitunc(p):
            if p[1:2] == ':':
                return '', p # Drive letter present
            firstTwo = p[0:2]
            if firstTwo == '//' or firstTwo == '\\\\':
                # is a UNC path:
                # vvvvvvvvvvvvvvvvvvvv equivalent to drive letter
                # \\machine\mountpoint\directories...
                #           directory ^^^^^^^^^^^^^^^
                normp = os.path.normcase(p)
                index = normp.find('\\', 2)
                if index == -1:
                    ##raise RuntimeError, 'illegal UNC path: "' + p + '"'
                    return ("", p)
                index = normp.find('\\', index + 1)
                if index == -1:
                    index = len(p)
                return p[:index], p[index:]
            return '', p
            
        def relpath(path, start=os.path.curdir):
            """Return a relative version of a path"""

            if not path:
                raise ValueError("no path specified")
            start_list = os.path.abspath(start).split(os.path.sep)
            path_list = os.path.abspath(path).split(os.path.sep)
            if start_list[0].lower() != path_list[0].lower():
                unc_path, rest = splitunc(path)
                unc_start, rest = splitunc(start)
                if bool(unc_path) ^ bool(unc_start):
                    raise ValueError("Cannot mix UNC and non-UNC paths (%s and %s)"
                                                                        % (path, start))
                else:
                    raise ValueError("path is on drive %s, start on drive %s"
                                                        % (path_list[0], start_list[0]))
            # Work out how much of the filepath is shared by start and path.
            for i in range(min(len(start_list), len(path_list))):
                if start_list[i].lower() != path_list[i].lower():
                    break
            else:
                i += 1

            rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
            if not rel_list:
                return os.path.curdir
            return os.path.join(*rel_list)
    else:
        def relpath(path, start=os.path.curdir):
            """Return a relative version of a path"""

            if not path:
                raise ValueError("no path specified")

            start_list = os.path.abspath(start).split(os.path.sep)
            path_list = os.path.abspath(path).split(os.path.sep)

            # Work out how much of the filepath is shared by start and path.
            i = len(os.path.commonprefix([start_list, path_list]))

            rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
            if not rel_list:
                return os.path.curdir
            return os.path.join(*rel_list)
else:
    relpath = os.path.relpath

def split_path(path):
    parts = []
    while True:
        head, tail = os.path.split(path)
        parts = [tail] + parts
        path = head
        if not path: break
    return parts

VALID_DB_NAME = re.compile(r'^[a-z][a-z0-9_$()+-/]*$')
SPECIAL_DBS = ("_users", "_replicator",)
def validate_dbname(name):
    """ validate dbname """
    if name in SPECIAL_DBS:
        return True
    elif not VALID_DB_NAME.match(urllib.unquote(name)):
        raise ValueError("Invalid db name: '%s'" % name)
    return True

def to_bytestring(s):
    """ convert to bytestring an unicode """
    if not isinstance(s, basestring):
        return s
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        return s
    
def read_file(fname, utf8=True, force_read=False):
    """ read file content"""
    if utf8:
        try:
            with codecs.open(fname, 'rb', "utf-8") as f:
                data = f.read()
                return data
        except UnicodeError:
            if force_read:
                return read_file(fname, utf8=False)
            raise
    else:
        with open(fname, 'rb') as f:
            data = f.read()
            return data

def sign_file(file_path):
    """ return md5 hash from file content
    
    :attr file_path: string, path of file
    
    :return: string, md5 hexdigest
    """
    if os.path.isfile(file_path):
        content = read_file(file_path, force_read=True)
        return md5(to_bytestring(content)).hexdigest()
    return ''

def write_content(fname, content):
    """ write content in a file
    
    :attr fname: string,filename
    :attr content: string
    """
    f = open(fname, 'wb')
    f.write(to_bytestring(content))
    f.close()

def write_json(filename, content):
    """ serialize content in json and save it
    
    :attr filename: string
    :attr content: string
    
    """
    write_content(filename, json.dumps(content))

def read_json(filename, use_environment=False):
    """ read a json file and deserialize
    
    :attr filename: string
    :attr use_environment: boolean, default is False. If
    True, replace environment variable by their value in file
    content
    
    :return: dict or list
    """
    try:
        data = read_file(filename, force_read=True)
    except IOError, e:
        if e[0] == 2:
            return {}
        raise

    if use_environment:
        data = string.Template(data).substitute(os.environ)

    try:
        data = json.loads(data)
    except ValueError:
        print >>sys.stderr, "Json is invalid, can't load %s" % filename
        raise
    return data



########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

version_info = (0, 6, 5)
__version__ =  ".".join(map(str, version_info))

########NEW FILE########
__FILENAME__ = handler
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import sys
import StringIO
import traceback
from urllib import unquote

from restkit.util import url_encode

from .. import __version__
from ..external import External

def _normalize_name(name):
    return  "-".join([w.lower().capitalize() for w in name.split("-")])

class WSGIRequest(object):
    
    SERVER_VERSION = "couchdbkit/%s" % __version__
    
    def __init__(self, line):
        self.line = line
        self.response_status = 200
        self.response_headers = {}
        self.start_response_called = False
    
    def read(self):
        headers = self.parse_headers()
        
        length = headers.get("CONTENT_LENGTH")
        if self.line["body"] and self.line["body"] != "undefined":
            length = len(self.line["body"])
            body = StringIO.StringIO(self.line["body"])
            
        else:
            body = StringIO.StringIO()
            
        # path
        script_name, path_info = self.line['path'][:2],  self.line['path'][2:]
        if path_info:
            path_info = "/%s" % "/".join(path_info)
        else: 
            path_info = ""
        script_name = "/%s" % "/".join(script_name)

        # build query string
        args = []
        query_string = None
        for k, v in self.line["query"].items():
            if v is None:
                continue
            else:
                args.append((k,v))       
        if args: query_string = url_encode(dict(args))
        
        # raw path could be useful
        path = "%s%s" % (path_info, query_string)
                
        # get server address
        if ":" in self.line["headers"]["Host"]:
            server_address = self.line["headers"]["Host"].split(":")
        else:
            server_address = (self.line["headers"]["Host"], 80)

        environ = {
            "wsgi.url_scheme": 'http',
            "wsgi.input": body,
            "wsgi.errors": StringIO.StringIO(),
            "wsgi.version": (1, 0),
            "wsgi.multithread": False,
            "wsgi.multiprocess": True,
            "wsgi.run_once": False,
            "SCRIPT_NAME": script_name,
            "SERVER_SOFTWARE": self.SERVER_VERSION,
            "COUCHDB_INFO": self.line["info"],
            "COUCHDB_REQUEST": self.line,
            "REQUEST_METHOD": self.line["verb"].upper(),
            "PATH_INFO": unquote(path_info),
            "QUERY_STRING": query_string,
            "RAW_URI": path,
            "CONTENT_TYPE": headers.get('CONTENT-TYPE', ''),
            "CONTENT_LENGTH": length,
            "REMOTE_ADDR": self.line['peer'],
            "REMOTE_PORT": 0,
            "SERVER_NAME": server_address[0],
            "SERVER_PORT": int(server_address[1]),
            "SERVER_PROTOCOL": "HTTP/1.1"
        }
        
        for key, value in headers.items():
            key = 'HTTP_' + key.replace('-', '_')
            if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
                environ[key] = value
                
        return environ
        
    def start_response(self, status, response_headers):
        self.response_status = int(status.split(" ")[0])
        for name, value in response_headers:
            name = _normalize_name(name)
            self.response_headers[name] = value.strip()
        self.start_response_called = True
                
    def parse_headers(self):
        headers = {}
        for name, value in self.line.get("headers", {}).items():
            name = name.strip().upper().encode("utf-8")
            headers[name] = value.strip().encode("utf-8")
        return headers

class WSGIHandler(External):
    
    def __init__(self, application, stdin=sys.stdin, 
            stdout=sys.stdout):
        External.__init__(self, stdin=stdin, stdout=stdout)
        self.app = application
    
    def handle_line(self, line):
        try:
            req = WSGIRequest(line)
            response = self.app(req.read(), req.start_response)
        except:
            self.send_response(500, "".join(traceback.format_exc()), 
                    {"Content-Type": "text/plain"})
            return 
            
        content = "".join(response).encode("utf-8")    
        self.send_response(req.response_status, content, req.response_headers)
    
    

########NEW FILE########
__FILENAME__ = proxy
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import urlparse

from restkit.contrib.wsgi_proxy import HostProxy, ALLOWED_METHODS
from webob import Request

class CouchdbProxy(object):
    """\
    WSGI application to proxy a couchdb server.
    
    Simple usage to proxy a CouchDB server on default url::
    
        from couchdbkit.wsgi import CouchdbProxy
        application = CouchdbProxy()
    """
    
    def __init__(self, uri="http://127.0.0.1:5984",
            allowed_method=ALLOWED_METHODS, **kwargs):
        self.proxy = HostProxy(uri,  allowed_methods=allowed_method,
                **kwargs)

    def do_proxy(self, req, environ, start_response):
        """\
        return proxy response. Can be overrided to add authentification and 
        such. It's better to override do_proxy method than the __call__
        """
        return req.get_response(self.proxy)

    def __call__(self, environ, start_response):
        req = Request(environ)
        if 'RAW_URI' in req.environ:
            # gunicorn so we can use real path non encoded
            u = urlparse.urlparse(req.environ['RAW_URI'])
            req.environ['PATH_INFO'] = u.path
            
        resp = self.do_proy(req, environ, start_response)
        return resp(environ, start_response)

########NEW FILE########
__FILENAME__ = buildweb
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2008-2009 Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import with_statement

import codecs
import datetime
import os
import re
from stat import *
import sys

from jinja2 import Environment
from jinja2.loaders import FileSystemLoader
from jinja2.utils import open_if_exists
try:
    import markdown
except ImportError:
    markdown = None
    
try:
    from textile import textile
except ImportError:
    textile = None
    
import PyRSS2Gen

import conf


# could be better
re_date = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])-(.*)$')


template_env = Environment(loader=FileSystemLoader(conf.TEMPLATES_PATH, encoding="utf-8"))
template_env.charset = 'utf-8'

def render_template(template_name, _stream=False, **kwargs):
    """ render jinja template """
    tmpl = template_env.get_template(template_name)
    context = kwargs
    if _stream:
        return tmpl.stream(context)
    return tmpl.render(context)
    
def relative_url(value):
    site_url = conf.SITE_URL
    if site_url.endswith('/'):
        site_url = site_url[:-1]
    return value.split(site_url)[1]
template_env.filters['rel_url'] = relative_url
    
def source_newer(source, target):
    if len(sys.argv) > 1 and sys.argv[1] == "force":
        return True

    if not os.path.exists(target): 
        return True
    else:
        smtime = os.stat(source)[ST_MTIME]
        tmtime = os.stat(target)[ST_MTIME]
        return smtime > tmtime

   
def convert_markdown(value):
    md = markdown.Markdown(output_format="html")
    md.set_output_format('html')
    return md.convert(value)
    
def convert_textile(value):
    return textile(value, head_offset=False, encoding='utf-8', 
                output='utf-8').decode('utf-8')
            
def rfc3339_date(date):
    # iso8601
    if date.tzinfo:
        return date.strftime('%Y-%m-%dT%H:%M:%S%z')
    else:
        return date.strftime('%Y-%m-%dT%H:%M:%SZ')

    
class Site(object):    
    def __init__(self):
        self.sitemap = []
        self.feed = []
        site_url = conf.SITE_URL
        if site_url.endswith('/'):
            site_url = site_url[:-1]
        self.site_url = site_url

    def process_directory(self, current_dir, files, target_path):
        files = [f for f in files if os.path.splitext(f)[1] in conf.EXTENSIONS]
        blog = None
        for f in files:
            print "process %s" % f
            page = Page(self, f, current_dir, target_path)
            if page.is_blog() and f == "index.txt" or f == "archives.txt":
                continue
            elif page.is_blog():
                if blog is None:
                    blog = Blog(self, current_dir, target_path)
                blog.append(page)
                continue
                
            if not source_newer(page.finput, page.foutput) and f != "index.txt":
                continue
                
            print "write %s" % page.foutput
            try:
                f = codecs.open(page.foutput, 'w', 'utf-8')
                try:
                    f.write(page.render())
                finally:
                    f.close()
            except (IOError, OSError), err:
                raise
            self.sitemap.append(page)
        if blog is not None:
            blog.render()    
        
    def generate_rss(self):
        rss = PyRSS2Gen.RSS2(
            title = conf.SITE_NAME,
            link = conf.SITE_URL,
            description = conf.SITE_DESCRIPTION,
            lastBuildDate = datetime.datetime.utcnow(),
            items = [])
        for i, e in enumerate(self.feed):
            item = PyRSS2Gen.RSSItem(
                    title = e['title'],
                    link = e['link'],
                    description = e['description'],
                    guid = PyRSS2Gen.Guid(e['link']),
                    pubDate = datetime.datetime.fromtimestamp(e['pubDate']))
            rss.items.append(item)
            if i == 15: break
        rss.write_xml(open(os.path.join(conf.OUTPUT_PATH, "feed.xml"), "w"))
        
    def generate_sitemap(self):
        xml = u'<?xml version="1.0" encoding="UTF-8"?>'
        xml += u'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        for page in self.sitemap:
            xml += u'<url>'
            xml += u'<loc>%s</loc>' % page.url
            xml += u'<lastmod>%s</lastmod>' % rfc3339_date(page.headers['published'])
            xml += u'<changefreq>daily</changefreq>'
            xml += u'<priority>0.5</priority>'
            xml += u'</url>'
        xml += u'</urlset>'
        with codecs.open(os.path.join(conf.OUTPUT_PATH, "sitemaps.xml"), "w", "utf-8") as f:
            f.write(xml)
            
            
    def render(self):
        for root, dirs, files in os.walk(conf.INPUT_PATH):
            target_path = root.replace(conf.INPUT_PATH, conf.OUTPUT_PATH)
            if not os.path.isdir(target_path):
                os.makedirs(target_path)
            self.process_directory(root, files, target_path)
            
        if self.feed:
            self.feed.sort(lambda a, b: a['pubDate'] - b['pubDate'], reverse=True)
            self.generate_rss()
        
        if self.sitemap:
            self.generate_sitemap()        

class Blog(object):
    
    def __init__(self, site, current_dir, target_path):
        self.site = site
        self.current_dir = current_dir
        self.target_path = target_path
        self.pages = []
        
    def append(self, page):
        paras = [p for p in page.body.split("\n\n") if p]
        if paras:
            description = "\n\n".join(paras[0:2])
            content_type = page.headers.get('content_type', conf.CONTENT_TYPE)
            if content_type == "markdown":
                description = convert_markdown(description)
            elif content_type == "textile":
                description = convert_textile(description)
        
        m = re_date.match(os.path.splitext(page.filename)[0])
        if m:
            date = "%s-%s-%s" % (m.group(1), m.group(2), m.group(3))
        else:
            date = ""
        page.headers['date'] = date
        
        page.headers['description'] = description
        self.pages.append(page)
        
    def render(self):
        index_page = Page(self.site, "index.txt", self.current_dir, 
            self.target_path)
            
        try:
            archives_page = Page(self.site, "archives.txt", self.current_dir, 
                self.target_path)
        except IOError:
            archives_page = None
            
        if not os.path.isfile(index_page.finput):
            raise IOError, "index.txt isn't found in %s" % self.current_dir
        
            
        self.pages.sort(lambda a, b: a.headers['pubDate'] - b.headers['pubDate'], reverse=True)
        entries = []
        # first pass
        for page in self.pages:
            entry =  {
                "title": page.headers.get('title', page.filename),
                "description":  page.headers['description'],
                "link": page.url,
                "pubDate": page.headers['pubDate'],
                "date": page.headers['date']
            }
            self.site.feed.append(entry)
            entries.append(entry)
            
        self.pages.append(index_page)
        
        if archives_page is not None:
            self.pages.append(archives_page)
        
        # second pass : render pages
        for page in self.pages:
            page.headers['entries'] = entries
            try:
                f = codecs.open(page.foutput, 'w', 'utf-8')
                try:
                    f.write(page.render())
                finally:
                    f.close()
            except (IOError, OSError), err:
                raise
            self.site.sitemap.append(page)

class Page(object):
    content_types = {
        'html': 'text/html',
        'markdown': 'text/html',
        'textile': 'text/html',
        'text': 'text/plain'
    }
    
    files_ext = {
        'html': 'html',
        'markdown': 'html',
        'textile': 'html',
        'text': 'txt'
    }
    
    def __init__(self, site, filename, current_dir, target_path):
        self.filename = filename
        self.current_dir = current_dir
        self.target_path = target_path
        self.finput = os.path.join(current_dir, filename)
        self.parsed = False
        self.foutput = ''
        self.site = site
        self.headers = {}
        self.body = ""
        self.parse()
   
    def get_url(self):
        rel_path = self.foutput.split(conf.OUTPUT_PATH)[1]
        if rel_path.startswith('/'):
            rel_path = rel_path[1:]    
        return "/".join([self.site.site_url, rel_path])
        
    def parse(self):
        with open(self.finput, 'r') as f:
            headers = {}
            raw = f.read()
            try:
                (header_lines,body) = raw.split("\n\n", 1)
                for header in header_lines.split("\n"):
                    (name, value) = header.split(": ", 1)
                    headers[name.lower()] = unicode(value.strip())
                self.headers = headers
                self.headers['pubDate'] = os.stat(self.finput)[ST_CTIME]
                self.headers['published'] = datetime.datetime.fromtimestamp(self.headers['pubDate'])
                self.body = body
                content_type = self.headers.get('content_type', conf.CONTENT_TYPE)
                if content_type in self.content_types.keys(): 
                    self.foutput = os.path.join(self.target_path, 
                            "%s.%s" % (os.path.splitext(self.filename)[0], self.files_ext[content_type]))
                    self.url = self.get_url()
                else:
                    raise TypeError, "Unknown content_type" 
            except:
                raise TypeError, "Invalid page file format for %s" % self.finput
            self.parsed = True
                
    def is_blog(self):
        if not 'page_type' in self.headers:
            return False
        return (self.headers['page_type'] == "blog")

    def render(self):
        if not self.parsed:
            self.parse()
        template = self.headers.get('template', conf.DEFAULT_TEMPLATE)
        content_type = self.headers.get('content_type', conf.CONTENT_TYPE)
        if content_type in self.content_types.keys():
            fun = getattr(self, "render_%s" % content_type)
            return fun(template)
        else:
            raise TypeError, "Unknown content_type" 

    def _render_html(self, template, body):
        kwargs = {
            "body": body,
            "sitename": conf.SITE_NAME,
            "siteurl": conf.SITE_URL,
            "url": self.url
        }
        kwargs.update(self.headers)
        return render_template(template, **kwargs)
        
    def render_html(self, template):
        return self._render_html(template, self.body)
        
    def render_markdown(self, template):
        if markdown is None:
            raise TypeError, "markdown isn't suported"
        body = convert_markdown(self.body)
        return self._render_html(template, body)
        
    def render_textile(self, template):
        if textile is None:
            raise TypeError, "textile isn't suported"
        body = convert_textile(self.body)
        return self._render_html(template, body)
        
    def render_text(self, template):
        return self.body
    
def main():
    site = Site()
    site.render()
    
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
import os, platform

# options
SITE_NAME = "Couchdbkit"
SITE_URL = "http://www.couchdbkit.org"
SITE_DESCRIPTION = "CouchdDB python framework"


EXTENSIONS = ['.txt', '.md', '.markdown']
DEFAULT_TEMPLATE = "default.html"
CONTENT_TYPE = "textile"


# paths 
DOC_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.join(DOC_PATH, "templates")
INPUT_PATH = os.path.join(DOC_PATH, "site")
OUTPUT_PATH = os.path.join(DOC_PATH, "htdocs")
########NEW FILE########
__FILENAME__ = models
from datetime import datetime
from django.db import models

from couchdbkit.ext.django.schema import *

class Greeting(Document):
    author = StringProperty()
    content = StringProperty(required=True)
    date = DateTimeProperty(default=datetime.utcnow)
    
    class Meta:
        app_label = "greeting"

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

from datetime import datetime
from django.shortcuts import render_to_response as render
from django.template import RequestContext, loader, Context

from couchdbkit.ext.django.forms import DocumentForm

from djangoapp.greeting.models import Greeting


class GreetingForm(DocumentForm):
    
    class Meta:
        document = Greeting


def home(request):
    
    greet = None
    
    if request.POST:
        form = GreetingForm(request.POST)
        if form.is_valid():
            greet = form.save()  
    else:
        form = GreetingForm()
        
    greetings = Greeting.view('greeting/all', descending=True)
    
    return render("home.html", {
        "form": form,
        "greet": greet,
        "greetings": greetings
    }, context_instance=RequestContext(request))
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = run
#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008,2009 Benoit Chesneau <benoitc@e-engura.org>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at#
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from couchdbkit.wsgi.handler import WSGIHandler
import os
import sys

PROJECT_PATH = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(PROJECT_PATH)

os.environ['DJANGO_SETTINGS_MODULE'] = 'djangoapp.settings'

import django.core.handlers.wsgi
app = django.core.handlers.wsgi.WSGIHandler()

def main():
    handler = WSGIHandler(app)
    handler.run()
    
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = settings
# Django settings for testapp project.

import os, platform

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Benoit Chesneau', 'bchesneau@gmail.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'test.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

COUCHDB_DATABASES = (
    ('djangoapp.greeting', 'http://127.0.0.1:5984/greeting'),
)

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Paris'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_PATH, 'static')

MEDIA_URL = '/media'

ADMIN_MEDIA_PREFIX = '/admin/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '3c7!ofj2o@7vglv+dj(pm_2_m*n)4qnfi7cw+7#8c3ng6sxcml'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'djangoapp.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_PATH, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'couchdbkit.ext.django',
    'djangoapp.greeting'
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'djangoapp.greeting.views.home'),
)


########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from couchdbkit.ext.django.schema import Document, StringProperty, \
    DateTimeProperty


class Post(Document):
    author = StringProperty()
    title = StringProperty()
    content = StringProperty()
    date = DateTimeProperty(default=datetime.utcnow)

class Comment(Document):
    author = StringProperty()
    content = StringProperty()
    date = DateTimeProperty(default=datetime.utcnow)
    post = StringProperty()

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
from couchdbkit.ext.django.forms import DocumentForm
from django.forms.fields import CharField
from django.forms.widgets import HiddenInput
from django.shortcuts import render_to_response
from django.template import RequestContext

from models import Post, Comment


class PostForm(DocumentForm):
    
    class Meta:
        document = Post
        
class CommentForm(DocumentForm):

    post = CharField(widget=HiddenInput(), required=False)

    class Meta:
        document = Comment

def home(request):
    post = None
    form = PostForm(request.POST or None)
    
    if request.POST:
        if form.is_valid():
            post = form.save()

    posts = Post.view('blog_app/all_posts', descending=True)
    
    return render_to_response("home.html", {
        "form": form,
        "post": post,
        "posts": posts
    }, context_instance=RequestContext(request))

def view_post(request, post_id):
    post = Post.get(post_id)
    form = CommentForm(request.POST or None)

    if request.POST:
        if form.is_valid():
            form.cleaned_data['post'] = post_id
            form.save()

    comments = Comment.view('blog_app/commets_by_post', key=post_id)
    
    return render_to_response("post_details.html", {
        "form": form,
        "post": post,
        "comments": comments
    }, context_instance=RequestContext(request))

def edit_post(request, post_id):
    post = Post.get(post_id)
    form = PostForm(request.POST or None, instance=post)
    
    if form.is_valid():
        post = form.save()
    
    return render_to_response("post_edit.html", {
        "form": form,
        "post": post
    }, context_instance=RequestContext(request))
########NEW FILE########
__FILENAME__ = settings
# Django settings for django_blogapp project.
import os

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'test.db',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

COUCHDB_DATABASES = (
    ('django_blogapp.blog_app', 'http://127.0.0.1:5984/blog_app'),
)

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Argentina/Buenos_Aires'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'es-AR'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '2+mptb$5$p0-w!q6u4=6pt)mjrf6+u&26jr65-e!3ax+4fo#r*'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'django_blogapp.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'django_blogapp.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_PATH, 'templates'),
)

INSTALLED_APPS = (
    'couchdbkit.ext.django',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'django_blogapp.blog_app',
)

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url


urlpatterns = patterns('',
    url(r'^$', 'django_blogapp.blog_app.views.home'),
    url(r'^post/(?P<post_id>\w*)/$', 'django_blogapp.blog_app.views.view_post'),
    url(r'^post/edit/(?P<post_id>\w*)/$', 'django_blogapp.blog_app.views.edit_post'),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for django_blogapp project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "django_blogapp.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_blogapp.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = tests
import unittest

from pyramid import testing

class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_my_view(self):
        from .views import my_view
        #Don't actually test anything right now
        #request = testing.DummyRequest()
        #info = my_view(request)
        #self.assertEqual(info['project'], 'pyramid_couchdb_example')
        self.assertEqual(True, True)

########NEW FILE########
__FILENAME__ = views
import datetime

from pyramid.view import view_config

from couchdbkit import *

import logging
log = logging.getLogger(__name__)

class Page(Document):
    author = StringProperty()
    page = StringProperty()
    content = StringProperty()
    date = DateTimeProperty()

@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):

    def get_data():
        return list(request.db.view('lists/pages', startkey=['home'], \
                endkey=['home', {}], include_docs=True))

    page_data = get_data()

    if not page_data:
        Page.set_db(request.db)
        home = Page(
            author='Wendall',
            content='Using CouchDB via couchdbkit!',
            page='home',
            date=datetime.datetime.utcnow()
        )
        # save page data
        home.save()

        page_data = get_data()

    doc = page_data[0].get('doc')

    return {
        'project': 'pyramid_couchdb_example',
        'info': request.db.info(),
        'author': doc.get('author'),
        'content': doc.get('content'),
        'date': doc.get('date')
    }

########NEW FILE########
__FILENAME__ = test
#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008,2009 Benoit Chesneau <benoitc@e-engura.org>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at#
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import couchdbkit
from couchdbkit.contrib import WSGIHandler
import json

def app(environ, start_response):
    """Simplest possible application object"""
    data = 'Hello, World!\n DB Infos : %s\n'  % json.dumps(environ["COUCHDB_INFO"])
    status = '200 OK'
    response_headers = [
        ('Content-type','text/plain'),
        ('Content-Length', len(data))
    ]
    start_response(status, response_headers)
    return [data]
    
def main():
    handler = WSGIHandler(app)
    handler.run()
    
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = client_test
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.
#
__author__ = 'benoitc@e-engura.com (Benoît Chesneau)'

import copy
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from couchdbkit import ResourceNotFound, RequestFailed, \
ResourceConflict

from couchdbkit import *


class ClientServerTestCase(unittest.TestCase):
    def setUp(self):
        self.couchdb = CouchdbResource()
        self.Server = Server()

    def tearDown(self):
        try:
            del self.Server['couchdbkit_test']
            del self.Server['couchdbkit/test']
        except:
            pass

    def testGetInfo(self):
        info = self.Server.info()
        self.assert_(info.has_key('version'))

    def testCreateDb(self):
        res = self.Server.create_db('couchdbkit_test')
        self.assert_(isinstance(res, Database) == True)
        all_dbs = self.Server.all_dbs()
        self.assert_('couchdbkit_test' in all_dbs)
        del self.Server['couchdbkit_test']
        res = self.Server.create_db("couchdbkit/test")
        self.assert_('couchdbkit/test' in self.Server.all_dbs())
        del self.Server['couchdbkit/test']

    def testGetOrCreateDb(self):
        # create the database
        gocdb = self.Server.get_or_create_db("get_or_create_db")
        self.assert_(gocdb.dbname == "get_or_create_db")
        self.assert_("get_or_create_db" in self.Server)
        self.Server.delete_db("get_or_create_db")
        # get the database (already created)
        self.assertFalse("get_or_create_db" in self.Server)
        db = self.Server.create_db("get_or_create_db")
        self.assert_("get_or_create_db" in self.Server)
        gocdb = self.Server.get_or_create_db("get_or_create_db")
        self.assert_(db.dbname == gocdb.dbname)
        self.Server.delete_db("get_or_create_db")


    def testCreateInvalidDbName(self):

        def create_invalid():
            res = self.Server.create_db('123ab')

        self.assertRaises(ValueError, create_invalid)

    def testServerLen(self):
        res = self.Server.create_db('couchdbkit_test')
        self.assert_(len(self.Server) >= 1)
        self.assert_(bool(self.Server))
        del self.Server['couchdbkit_test']

    def testServerContain(self):
        res = self.Server.create_db('couchdbkit_test')
        self.assert_('couchdbkit_test' in self.Server)
        del self.Server['couchdbkit_test']


    def testGetUUIDS(self):
        uuid = self.Server.next_uuid()
        self.assert_(isinstance(uuid, basestring) == True)
        self.assert_(len(self.Server._uuids) == 999)
        uuid2 = self.Server.next_uuid()
        self.assert_(uuid != uuid2)
        self.assert_(len(self.Server._uuids) == 998)

class ClientDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.couchdb = CouchdbResource()
        self.Server = Server()

    def tearDown(self):
        try:
            del self.Server['couchdbkit_test']
        except:
            pass

    def testCreateDatabase(self):
        db = self.Server.create_db('couchdbkit_test')
        self.assert_(isinstance(db, Database) == True)
        info = db.info()
        self.assert_(info['db_name'] == 'couchdbkit_test')
        del self.Server['couchdbkit_test']

    def testDbFromUri(self):
        db = self.Server.create_db('couchdbkit_test')

        db1 = Database("http://127.0.0.1:5984/couchdbkit_test")
        self.assert_(hasattr(db1, "dbname") == True)
        self.assert_(db1.dbname == "couchdbkit_test")
        info = db1.info()
        self.assert_(info['db_name'] == "couchdbkit_test")


    def testCreateEmptyDoc(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = {}
        db.save_doc(doc)
        del self.Server['couchdbkit_test']
        self.assert_('_id' in doc)


    def testCreateDoc(self):
        db = self.Server.create_db('couchdbkit_test')
        # create doc without id
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        self.assert_(db.doc_exist(doc['_id']))
        # create doc with id
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4 }
        db.save_doc(doc1)
        self.assert_(db.doc_exist('test'))
        doc2 = { 'string': 'test', 'number': 4 }
        db['test2'] = doc2
        self.assert_(db.doc_exist('test2'))
        del self.Server['couchdbkit_test']

        db = self.Server.create_db('couchdbkit/test')
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4 }
        db.save_doc(doc1)
        self.assert_(db.doc_exist('test'))
        del self.Server['couchdbkit/test']

    def testUpdateDoc(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        doc.update({'number': 6})
        db.save_doc(doc)
        doc = db.get(doc['_id'])
        self.assert_(doc['number'] == 6)
        del self.Server['couchdbkit_test']

    def testDocWithSlashes(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { '_id': "a/b"}
        db.save_doc(doc)
        self.assert_( "a/b" in db)

        doc = { '_id': "http://a"}
        db.save_doc(doc)
        self.assert_( "http://a" in db)
        doc = db.get("http://a")
        self.assert_(doc is not None)

        def not_found():
            doc = db.get('http:%2F%2Fa')
        self.assertRaises(ResourceNotFound, not_found)

        self.assert_(doc.get('_id') == "http://a")
        doc.get('_id')

        doc = { '_id': "http://b"}
        db.save_doc(doc)
        self.assert_( "http://b" in db)

        doc = { '_id': '_design/a' }
        db.save_doc(doc)
        self.assert_( "_design/a" in db)
        del self.Server['couchdbkit_test']

    def testGetRev(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = {}
        db.save_doc(doc)
        rev = db.get_rev(doc['_id'])
        self.assert_(rev == doc['_rev'])

    def testForceUpdate(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = {}
        db.save_doc(doc)
        doc1 = doc.copy()
        db.save_doc(doc)
        self.assertRaises(ResourceConflict, db.save_doc, doc1)

        is_conflict = False
        try:
            db.save_doc(doc1, force_update=True)
        except ResourceConflict:
            is_conflict = True

        self.assert_(is_conflict == False)


    def testMultipleDocWithSlashes(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { '_id': "a/b"}
        doc1 = { '_id': "http://a"}
        doc3 = { '_id': '_design/a' }
        db.bulk_save([doc, doc1, doc3])
        self.assert_( "a/b" in db)
        self.assert_( "http://a" in db)
        self.assert_( "_design/a" in db)

        def not_found():
            doc = db.get('http:%2F%2Fa')
        self.assertRaises(ResourceNotFound, not_found)

    def testFlush(self):
        db = self.Server.create_db('couchdbkit_test')
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4 }
        db.save_doc(doc1)
        doc2 = { 'string': 'test', 'number': 4 }
        db['test2'] = doc2
        self.assert_(db.doc_exist('test'))
        self.assert_(db.doc_exist('test2'))
        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc);
            }}"""
                }
            }
        }
        db.save_doc(design_doc)
        db.put_attachment(design_doc, 'test', 'test', 'test/plain')
        self.assert_(len(db) == 3)
        db.flush()
        self.assert_(len(db) == 1)
        self.assertFalse(db.doc_exist('test'))
        self.assertFalse(db.doc_exist('test2'))
        self.assert_(db.doc_exist('_design/test'))
        ddoc = db.get("_design/test")
        self.assert_('all' in ddoc['views'])
        self.assert_('test' in ddoc['_attachments'])
        del self.Server['couchdbkit_test']

    def testDbLen(self):
        db = self.Server.create_db('couchdbkit_test')
        doc1 = { 'string': 'test', 'number': 4 }
        db.save_doc(doc1)
        doc2 = { 'string': 'test2', 'number': 4 }
        db.save_doc(doc2)

        self.assert_(len(db) == 2)
        del self.Server['couchdbkit_test']

    def testDeleteDoc(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        docid=doc['_id']
        db.delete_doc(docid)
        self.assert_(db.doc_exist(docid) == False)
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        docid=doc['_id']
        db.delete_doc(doc)
        self.assert_(db.doc_exist(docid) == False)

        del self.Server['couchdbkit_test']

    def testStatus404(self):
        db = self.Server.create_db('couchdbkit_test')

        def no_doc():
            doc = db.get('t')

        self.assertRaises(ResourceNotFound, no_doc)

        del self.Server['couchdbkit_test']

    def testInlineAttachments(self):
        db = self.Server.create_db('couchdbkit_test')
        attachment = "<html><head><title>test attachment</title></head><body><p>Some words</p></body></html>"
        doc = {
            '_id': "docwithattachment",
            "f": "value",
            "_attachments": {
                "test.html": {
                    "type": "text/html",
                    "data": attachment
                }
            }
        }
        db.save_doc(doc)
        fetch_attachment = db.fetch_attachment(doc, "test.html")
        self.assert_(attachment == fetch_attachment)
        doc1 = db.get("docwithattachment")
        self.assert_('_attachments' in doc1)
        self.assert_('test.html' in doc1['_attachments'])
        self.assert_('stub' in doc1['_attachments']['test.html'])
        self.assert_(doc1['_attachments']['test.html']['stub'] == True)
        self.assert_(len(attachment) == doc1['_attachments']['test.html']['length'])
        del self.Server['couchdbkit_test']

    def testMultipleInlineAttachments(self):
        db = self.Server.create_db('couchdbkit_test')
        attachment = "<html><head><title>test attachment</title></head><body><p>Some words</p></body></html>"
        attachment2 = "<html><head><title>test attachment</title></head><body><p>More words</p></body></html>"
        doc = {
            '_id': "docwithattachment",
            "f": "value",
            "_attachments": {
                "test.html": {
                    "type": "text/html",
                    "data": attachment
                },
                "test2.html": {
                    "type": "text/html",
                    "data": attachment2
                }
            }
        }

        db.save_doc(doc)
        fetch_attachment = db.fetch_attachment(doc, "test.html")
        self.assert_(attachment == fetch_attachment)
        fetch_attachment = db.fetch_attachment(doc, "test2.html")
        self.assert_(attachment2 == fetch_attachment)

        doc1 = db.get("docwithattachment")
        self.assert_('test.html' in doc1['_attachments'])
        self.assert_('test2.html' in doc1['_attachments'])
        self.assert_(len(attachment) == doc1['_attachments']['test.html']['length'])
        self.assert_(len(attachment2) == doc1['_attachments']['test2.html']['length'])
        del self.Server['couchdbkit_test']

    def testInlineAttachmentWithStub(self):
        db = self.Server.create_db('couchdbkit_test')
        attachment = "<html><head><title>test attachment</title></head><body><p>Some words</p></body></html>"
        attachment2 = "<html><head><title>test attachment</title></head><body><p>More words</p></body></html>"
        doc = {
            '_id': "docwithattachment",
            "f": "value",
            "_attachments": {
                "test.html": {
                    "type": "text/html",
                    "data": attachment
                }
            }
        }
        db.save_doc(doc)
        doc1 = db.get("docwithattachment")
        doc1["_attachments"].update({
            "test2.html": {
                "type": "text/html",
                "data": attachment2
            }
        })
        db.save_doc(doc1)

        fetch_attachment = db.fetch_attachment(doc1, "test2.html")
        self.assert_(attachment2 == fetch_attachment)

        doc2 = db.get("docwithattachment")
        self.assert_('test.html' in doc2['_attachments'])
        self.assert_('test2.html' in doc2['_attachments'])
        self.assert_(len(attachment) == doc2['_attachments']['test.html']['length'])
        self.assert_(len(attachment2) == doc2['_attachments']['test2.html']['length'])
        del self.Server['couchdbkit_test']

    def testAttachments(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        text_attachment = u"un texte attaché"
        old_rev = doc['_rev']
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = db.fetch_attachment(doc, "test")
        self.assert_(text_attachment == fetch_attachment)
        del self.Server['couchdbkit_test']

    def testFetchAttachmentStream(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        text_attachment = u"a text attachment"
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        stream = db.fetch_attachment(doc, "test", stream=True)
        fetch_attachment = stream.read()
        self.assert_(text_attachment == fetch_attachment)
        del self.Server['couchdbkit_test']

    def testEmptyAttachment(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = {}
        db.save_doc(doc)
        db.put_attachment(doc, "", name="test")
        doc1 = db.get(doc['_id'])
        attachment = doc1['_attachments']['test']
        self.assertEqual(0, attachment['length'])
        del self.Server['couchdbkit_test']

    def testDeleteAttachment(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)

        text_attachment = "un texte attaché"
        old_rev = doc['_rev']
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        db.delete_attachment(doc, 'test')
        self.assertRaises(ResourceNotFound, db.fetch_attachment, doc, 'test')
        del self.Server['couchdbkit_test']

    def testAttachmentsWithSlashes(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { '_id': 'test/slashes', 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        text_attachment = u"un texte attaché"
        old_rev = doc['_rev']
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = db.fetch_attachment(doc, "test")
        self.assert_(text_attachment == fetch_attachment)

        db.put_attachment(doc, text_attachment, "test/test.txt", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = db.fetch_attachment(doc, "test/test.txt")
        self.assert_(text_attachment == fetch_attachment)

        del self.Server['couchdbkit_test']


    def testAttachmentUnicode8URI(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { '_id': u"éàù/slashes", 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        text_attachment = u"un texte attaché"
        old_rev = doc['_rev']
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = db.fetch_attachment(doc, "test")
        self.assert_(text_attachment == fetch_attachment)
        del self.Server['couchdbkit_test']

    def testSaveMultipleDocs(self):
        db = self.Server.create_db('couchdbkit_test')
        docs = [
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 6 }
        ]
        db.bulk_save(docs)
        self.assert_(len(db) == 4)
        self.assert_('_id' in docs[0])
        self.assert_('_rev' in docs[0])
        doc = db.get(docs[2]['_id'])
        self.assert_(doc['number'] == 4)
        docs[3]['number'] = 6
        old_rev = docs[3]['_rev']
        db.bulk_save(docs)
        self.assert_(docs[3]['_rev'] != old_rev)
        doc = db.get(docs[3]['_id'])
        self.assert_(doc['number'] == 6)
        docs = [
                { '_id': 'test', 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { '_id': 'test2', 'string': 'test', 'number': 42 },
                { 'string': 'test', 'number': 6 }
        ]
        db.bulk_save(docs)
        doc = db.get('test2')
        self.assert_(doc['number'] == 42)
        del self.Server['couchdbkit_test']

    def testDeleteMultipleDocs(self):
        db = self.Server.create_db('couchdbkit_test')
        docs = [
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 6 }
        ]
        db.bulk_save(docs)
        self.assert_(len(db) == 4)
        db.bulk_delete(docs)
        self.assert_(len(db) == 0)
        self.assert_(db.info()['doc_del_count'] == 4)

        del self.Server['couchdbkit_test']

    def testMultipleDocCOnflict(self):
        db = self.Server.create_db('couchdbkit_test')
        docs = [
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 6 }
        ]
        db.bulk_save(docs)
        self.assert_(len(db) == 4)
        docs1 = [
                docs[0],
                docs[1],
                {'_id': docs[2]['_id'], 'string': 'test', 'number': 4 },
                {'_id': docs[3]['_id'], 'string': 'test', 'number': 6 }
        ]

        self.assertRaises(BulkSaveError, db.bulk_save, docs1)

        docs2 = [
            docs1[0],
            docs1[1],
            {'_id': docs[2]['_id'], 'string': 'test', 'number': 4 },
            {'_id': docs[3]['_id'], 'string': 'test', 'number': 6 }
        ]
        doc23 = docs2[3].copy()
        all_errors = []
        try:
            db.bulk_save(docs2)
        except BulkSaveError, e:
            all_errors = e.errors

        self.assert_(len(all_errors) == 2)
        self.assert_(all_errors[0]['error'] == 'conflict')
        self.assert_(doc23 == docs2[3])

        docs3 = [
            docs2[0],
            docs2[1],
            {'_id': docs[2]['_id'], 'string': 'test', 'number': 4 },
            {'_id': docs[3]['_id'], 'string': 'test', 'number': 6 }
        ]

        doc33 = docs3[3].copy()
        all_errors2 = []
        try:
            db.bulk_save(docs3, all_or_nothing=True)
        except BulkSaveError, e:
            all_errors2 = e.errors

        self.assert_(len(all_errors2) == 0)
        self.assert_(doc33 != docs3[3])
        del self.Server['couchdbkit_test']


    def testCopy(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { "f": "a" }
        db.save_doc(doc)

        db.copy_doc(doc['_id'], "test")
        self.assert_("test" in db)
        doc1 = db.get("test")
        self.assert_('f' in doc1)
        self.assert_(doc1['f'] == "a")

        db.copy_doc(doc, "test2")
        self.assert_("test2" in db)

        doc2 = { "_id": "test3", "f": "c"}
        db.save_doc(doc2)

        db.copy_doc(doc, doc2)
        self.assert_("test3" in db)
        doc3 = db.get("test3")
        self.assert_(doc3['f'] == "a")

        doc4 = { "_id": "test5", "f": "c"}
        db.save_doc(doc4)
        db.copy_doc(doc, "test6")
        doc6 = db.get("test6")
        self.assert_(doc6['f'] == "a")

        del self.Server['couchdbkit_test']

    def testSetSecurity(self):
        db = self.Server.create_db('couchdbkit_test')
        res = db.set_security({"meta": "test"})
        self.assert_(res['ok'] == True)
        del self.Server['couchdbkit_test']

    def testGetSecurity(self):
        db = self.Server.create_db('couchdbkit_test')
        db.set_security({"meta": "test"})
        res = db.get_security()
        self.assert_("meta" in res)
        self.assert_(res['meta'] == "test")
        del self.Server['couchdbkit_test']

class ClientViewTestCase(unittest.TestCase):
    def setUp(self):
        self.couchdb = CouchdbResource()
        self.Server = Server()

    def tearDown(self):
        try:
            del self.Server['couchdbkit_test']
        except:
            pass

        try:
            self.Server.delete_db('couchdbkit_test2')
        except:
            pass

    def testView(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4,
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc);
}}"""
                }
            }
        }
        db.save_doc(design_doc)

        doc3 = db.get('_design/test')
        self.assert_(doc3 is not None)
        results = db.view('test/all')
        self.assert_(len(results) == 2)
        del self.Server['couchdbkit_test']

    def test_view_indexing(self):
        db = self.Server.create_db('couchdbkit_test')
        viewres = db.view('test/test')
        assert 'limit' not in viewres.params
        limited = viewres[1:2]

    def test_view_subview(self):
        db = self.Server.create_db('couchdbkit_test')
        viewres = db.view('test/test')
        assert not viewres.params
        subviewres = viewres(key='a')
        self.assert_(subviewres.params)

    def testAllDocs(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4,
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)

        self.assert_(db.view('_all_docs').count() == 2 )
        self.assert_(db.view('_all_docs').all() == db.all_docs().all())

        del self.Server['couchdbkit_test']

    def testCount(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4,
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc); }}"""
                }
            }
        }
        db.save_doc(design_doc)
        count = db.view('/test/all').count()
        self.assert_(count == 2)
        del self.Server['couchdbkit_test']

    def testTemporaryView(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4,
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)

        design_doc = {
            "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc);
}}"""
        }

        results = db.temp_view(design_doc)
        self.assert_(len(results) == 2)
        del self.Server['couchdbkit_test']


    def testView2(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs
        doc1 = { '_id': 'test1', 'string': 'test', 'number': 4,
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)
        doc3 = { '_id': 'test3', 'string': 'test', 'number': 2,
                    'docType': 'test2'}
        db.save_doc(doc3)
        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'with_test': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc);
}}"""
                },
                'with_test2': {
                    "map": """function(doc) { if (doc.docType == "test2") { emit(doc._id, doc);
}}"""
                }

            }
        }
        db.save_doc(design_doc)

        # yo view is callable !
        results = db.view('test/with_test')
        self.assert_(len(results) == 2)
        results = db.view('test/with_test2')
        self.assert_(len(results) == 1)
        del self.Server['couchdbkit_test']

    def testViewWithParams(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs
        doc1 = { '_id': 'test1', 'string': 'test', 'number': 4,
                'docType': 'test', 'date': '20081107' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                'docType': 'test', 'date': '20081107'}
        db.save_doc(doc2)
        doc3 = { '_id': 'test3', 'string': 'machin', 'number': 2,
                    'docType': 'test', 'date': '20081007'}
        db.save_doc(doc3)
        doc4 = { '_id': 'test4', 'string': 'test2', 'number': 2,
                'docType': 'test', 'date': '20081108'}
        db.save_doc(doc4)
        doc5 = { '_id': 'test5', 'string': 'test2', 'number': 2,
                'docType': 'test', 'date': '20081109'}
        db.save_doc(doc5)
        doc6 = { '_id': 'test6', 'string': 'test2', 'number': 2,
                'docType': 'test', 'date': '20081109'}
        db.save_doc(doc6)

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'test1': {
                    "map": """function(doc) { if (doc.docType == "test")
                    { emit(doc.string, doc);
}}"""
                },
                'test2': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc.date, doc);
}}"""
                },
                'test3': {
                    "map": """function(doc) { if (doc.docType == "test")
                    { emit(doc.string, doc);
}}"""
                }


            }
        }
        db.save_doc(design_doc)

        results = db.view('test/test1')
        self.assert_(len(results) == 6)

        results = db.view('test/test3', key="test")
        self.assert_(len(results) == 2)



        results = db.view('test/test3', key="test2")
        self.assert_(len(results) == 3)

        results = db.view('test/test2', startkey="200811")
        self.assert_(len(results) == 5)

        results = db.view('test/test2', startkey="20081107",
                endkey="20081108")
        self.assert_(len(results) == 3)

        results = db.view('test/test1', keys=['test', 'machin'] )
        self.assert_(len(results) == 3)

        del self.Server['couchdbkit_test']


    def testMultiWrap(self):
        """
        Tests wrapping of view results to multiple
        classes using the client
        """

        class A(Document):
            pass
        class B(Document):
            pass

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { emit(doc._id, doc); }"""
                }
            }
        }
        a = A()
        a._id = "1"
        b = B()
        b._id = "2"
        db = self.Server.create_db('couchdbkit_test')
        A._db = db
        B._db = db

        a.save()
        b.save()
        db.save_doc(design_doc)
        # provide classes as a list
        results = list(db.view('test/all', schema=[A, B]))
        self.assert_(results[0].__class__ == A)
        self.assert_(results[1].__class__ == B)
        # provide classes as a dict
        results = list(db.view('test/all', schema={'A': A, 'B': B}))
        self.assert_(results[0].__class__ == A)
        self.assert_(results[1].__class__ == B)
        self.Server.delete_db('couchdbkit_test')


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_changes
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.
#
__author__ = 'benoitc@e-engura.com (Benoît Chesneau)'

import threading
import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from couchdbkit import *
from couchdbkit.changes import ChangesStream, fold, foreach

class ClientServerTestCase(unittest.TestCase):

    def setUp(self):
        self.server = Server()
        self._delete_db()
        self.db = self.server.create_db("couchdbkit_test")
        self.consumer = Consumer(self.db)

    def tearDown(self):
        self._delete_db()

    def _delete_db(self):
        try:
            del self.server['couchdbkit_test']
        except:
            pass


    def test_fetch(self):
        # save a doc
        doc = {}
        self.db.save_doc(doc)

        def fold_fun(c, acc):
            acc.append(c)
            return acc

        changes = fold(self.db, fold_fun, [])

        self.assert_(len(changes) == 1)
        change = changes[0]
        self.assert_(change["id"] == doc['_id'])


    def test_lonpoll(self):
        def test_change():
            with ChangesStream(self.db, feed="longpoll") as stream:
                for change in stream:
                    self.assert_(change["seq"] == 1)

        t = threading.Thread(target=test_change)
        t.daemon = True
        t.start()

        doc = {}
        self.db.save_doc(doc)


    def test_continuous(self):
        lines = []
        def test_change():
            with ChangesStream(self.db, feed="continuous") as stream:
                for change in stream:
                    lines.append(change)


        t = threading.Thread(target=test_change)
        t.daemon = True
        t.start()

        for i in range(5):
            doc = {"_id": "test%s" % str(i)}
            self.db.save_doc(doc)

        self.db.ensure_full_commit()
        time.sleep(0.3)
        self.assert_(len(lines) == 5)
        self.assert_(lines[4]["id"] == "test4")
        doc = {"_id": "test5"}
        self.db.save_doc(doc)
        time.sleep(0.3)
        self.assert_(len(lines) == 6)
        self.assert_(lines[5]["id"] == "test5")


########NEW FILE########
__FILENAME__ = test_consumer
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.
#
__author__ = 'benoitc@e-engura.com (Benoît Chesneau)'

import threading
import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from couchdbkit import *

class ClientServerTestCase(unittest.TestCase):

    def setUp(self):
        self.server = Server()
        self._delete_db()
        self.db = self.server.create_db("couchdbkit_test")
        self.consumer = Consumer(self.db)

    def tearDown(self):
        self._delete_db()

    def _delete_db(self):
        try:
            del self.server['couchdbkit_test']
        except:
            pass


    def test_fetch(self):
        res1 = self.consumer.fetch()
        self.assert_("last_seq" in res1)
        self.assert_(res1["last_seq"] == 0)
        self.assert_(res1["results"] == [])
        doc = {}
        self.db.save_doc(doc)
        res2 = self.consumer.fetch()
        self.assert_(res2["last_seq"] == 1)
        self.assert_(len(res2["results"]) == 1)
        line = res2["results"][0]
        self.assert_(line["id"] == doc["_id"])

    def test_longpoll(self):

        def test_line(line):
            self.assert_(line["last_seq"] == 1)
            self.assert_(len(line["results"]) == 1)
            return

        t =  threading.Thread(target=self.consumer.wait_once,
                kwargs=dict(cb=test_line))
        t.daemon = True
        t.start()
        doc = {}
        self.db.save_doc(doc)

    def test_continuous(self):
        self.lines = []
        def test_line(line):
            self.lines.append(line)

        t =  threading.Thread(target=self.consumer.wait,
                kwargs=dict(cb=test_line))
        t.daemon = True
        t.start()

        for i in range(5):
            doc = {"_id": "test%s" % str(i)}
            self.db.save_doc(doc)
        self.db.ensure_full_commit()
        time.sleep(0.3)
        self.assert_(len(self.lines) == 5)
        self.assert_(self.lines[4]["id"] == "test4")
        doc = {"_id": "test5"}
        self.db.save_doc(doc)
        time.sleep(0.3)
        self.assert_(len(self.lines) == 6)
        self.assert_(self.lines[5]["id"] == "test5")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_loaders
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.
#
__author__ = 'benoitc@e-engura.com (Benoît Chesneau)'

import base64
import os
import shutil
import tempfile
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from restkit import ResourceNotFound, RequestFailed

from couchdbkit import *
from couchdbkit.utils import *


class LoaderTestCase(unittest.TestCase):
    
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.template_dir = os.path.join(os.path.dirname(__file__), 'data/app-template')
        self.app_dir = os.path.join(self.tempdir, "couchdbkit-test")
        shutil.copytree(self.template_dir, self.app_dir)
        write_content(os.path.join(self.app_dir, "_id"),
                "_design/couchdbkit-test")
        self.server = Server()
        self.db = self.server.create_db('couchdbkit_test')
        
    def tearDown(self):
        for root, dirs, files in os.walk(self.tempdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

        os.rmdir(self.tempdir)
        del self.server['couchdbkit_test']
                
    def testGetDoc(self):
        l = FileSystemDocsLoader(self.tempdir)
        design_doc = l.get_docs()[0]
        self.assert_(isinstance(design_doc, dict))
        self.assert_('_id' in design_doc)
        self.assert_(design_doc['_id'] == "_design/couchdbkit-test")
        self.assert_('lib' in design_doc)
        self.assert_('helpers' in design_doc['lib'])
        self.assert_('template' in design_doc['lib']['helpers'])
        
    def testGetDocView(self):
        l = FileSystemDocsLoader(self.tempdir)
        design_doc = l.get_docs()[0]
        self.assert_('views' in design_doc)
        self.assert_('example' in design_doc['views'])
        self.assert_('map' in design_doc['views']['example'])
        self.assert_('emit' in design_doc['views']['example']['map'])
        
    def testGetDocCouchApp(self):
        l = FileSystemDocsLoader(self.tempdir)
        design_doc = l.get_docs()[0]
        self.assert_('couchapp' in design_doc)
        
    def testGetDocManifest(self):
        l = FileSystemDocsLoader(self.tempdir)
        design_doc = l.get_docs()[0]
        self.assert_('manifest' in design_doc['couchapp'])
        self.assert_('lib/helpers/template.js' in design_doc['couchapp']['manifest'])
        self.assert_('foo/' in design_doc['couchapp']['manifest'])
        self.assert_(len(design_doc['couchapp']['manifest']) == 16)
        
        
    def testGetDocAttachments(self):
        l = FileSystemDocsLoader(self.tempdir)
        design_doc = l.get_docs()[0]
        self.assert_('_attachments' in design_doc)
        self.assert_('index.html' in design_doc['_attachments'])
        self.assert_('style/main.css' in design_doc['_attachments'])
        
        content = design_doc['_attachments']['style/main.css']
        self.assert_(base64.b64decode(content['data']) == "/* add styles here */")
        
    def testGetDocSignatures(self):
        l = FileSystemDocsLoader(self.tempdir)
        design_doc = l.get_docs()[0]
        self.assert_('signatures' in design_doc['couchapp'])
        self.assert_(len(design_doc['couchapp']['signatures']) == 2)
        self.assert_('index.html' in design_doc['couchapp']['signatures'])
        signature =  design_doc['couchapp']['signatures']['index.html']
        fsignature = sign_file(os.path.join(self.app_dir, '_attachments/index.html'))
        self.assert_(signature==fsignature)
        
    def _sync(self, atomic=True):
        l = FileSystemDocsLoader(self.tempdir)
        l.sync(self.db, atomic=atomic, verbose=True)
        # any design doc created ?
        design_doc = None
        try:
            design_doc = self.db['_design/couchdbkit-test']
        except ResourceNotFound:
            pass
        self.assert_(design_doc is not None)
        

        # should create view
        self.assert_('function' in design_doc['views']['example']['map'])
        # should not create empty views
        self.assertFalse('empty' in design_doc['views'])
        self.assertFalse('wrong' in design_doc['views'])
        
        # should use macros
        self.assert_('stddev' in design_doc['views']['example']['map'])
        self.assert_('ejohn.org' in design_doc['shows']['example-show'])
        
        # should have attachments
        self.assert_('_attachments' in design_doc)
        
        # should create index
        self.assert_(design_doc['_attachments']['index.html']['content_type'] == 'text/html')
        
        # should create manifest
        self.assert_('foo/' in design_doc['couchapp']['manifest'])
        
        # should push and macro the doc shows
        self.assert_('Generated CouchApp Form Template' in design_doc['shows']['example-show'])
        
        # should push and macro the view lists
        self.assert_('Test XML Feed' in design_doc['lists']['feed'])
        
        # should allow deeper includes
        self.assertFalse('"helpers"' in design_doc['shows']['example-show'])
        
        # deep require macros
        self.assertFalse('"template"' in design_doc['shows']['example-show'])
        self.assert_('Resig' in design_doc['shows']['example-show'])
        
    def testSync(self):
        self._sync()
        
    def testSyncNonAtomic(self):
        self._sync(atomic=False)
        
if __name__ == '__main__':
    unittest.main()
        
        



########NEW FILE########
__FILENAME__ = test_resource
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.
#
__author__ = 'benoitc@e-engura.com (Benoît Chesneau)'

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from restkit.errors import RequestFailed, RequestError
from couchdbkit.resource import CouchdbResource


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.couchdb = CouchdbResource()
        try:
            self.couchdb.delete('/couchdkbit_test')
        except:
            pass
        
    def tearDown(self):
        self.couchdb = None
        try:
            self.couchdb.delete('/couchdkbit_test')
        except:
            pass

    def testGetInfo(self):
        info = self.couchdb.get().json_body
        self.assert_(info.has_key('version'))
        
    def testCreateDb(self):
        res = self.couchdb.put('/couchdkbit_test').json_body
        self.assert_(res['ok'] == True)
        all_dbs = self.couchdb.get('/_all_dbs').json_body
        self.assert_('couchdkbit_test' in all_dbs)
        self.couchdb.delete('/couchdkbit_test')

    def testCreateEmptyDoc(self):
        res = self.couchdb.put('/couchdkbit_test/').json_body
        self.assert_(res['ok'] == True)
        res = self.couchdb.post('/couchdkbit_test/', payload={}).json_body
        self.couchdb.delete('/couchdkbit_test')
        self.assert_(len(res) > 0)

    def testRequestFailed(self):
        bad = CouchdbResource('http://localhost:10000')
        self.assertRaises(RequestError, bad.get)
        
if __name__ == '__main__':
    unittest.main()



########NEW FILE########
__FILENAME__ = test_schema
# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

__author__ = 'benoitc@e-engura.com (Benoît Chesneau)'

import datetime
import decimal
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from couchdbkit import *
from couchdbkit.schema.properties import support_setproperty


class DocumentTestCase(unittest.TestCase):
    def setUp(self):
        self.server = Server()

    def tearDown(self):
        try:
            self.server.delete_db('couchdbkit_test')
        except:
            pass

        try:
            self.server.delete_db('couchdbkit_test2')
        except:
            pass

    def testStaticDocumentCreation(self):
        db = self.server.create_db('couchdbkit_test')

        # with _allow_dynamic_properties
        class Test(Document):
            _allow_dynamic_properties = False
            foo = StringProperty()
        Test._db = db

        doc = Test()
        doc.foo="test"
        try:
            doc.bar="bla"
        except AttributeError, e:
            self.assert_(str(e) == "bar is not defined in schema (not a valid property)")
        doc.save()
        self.assert_(not hasattr(doc, "bar"))
        assert doc._doc['foo'] == "test"

        # With StaticDocument
        class Test(StaticDocument):
            foo = StringProperty()
        Test._db = db

        doc = Test()
        doc.foo="test"
        try:
            doc.bar="bla"
        except AttributeError, e:
            self.assert_(str(e) == "bar is not defined in schema (not a valid property)")
        doc.save()
        self.assert_(not hasattr(doc, "bar"))
        self.assert_(doc._doc['foo'] == "test")

        doc1 = Test(foo="doc1")
        db.save_doc(doc1)
        self.assert_(doc1._doc['foo'] == "doc1")

        self.server.delete_db('couchdbkit_test')


    def testDocumentSetDbBooleanIssue(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            pass

        self.assertRaises(ResourceNotFound, Test.get, 'notthete', db=db)

        fun = Test.get_or_create('foo', db=db)
        self.assert_(fun._id == 'foo')

    def testDynamicDocumentCreation(self):
        class Test(Document):
            pass

        class Test2(Document):
            string = StringProperty(default="test")


        doc = Test(string="essai")
        self.assert_(getattr(doc, 'string') is not None)
        self.assert_(doc.string == "essai")

        doc1 = Test(string="essai", string2="essai2")
        self.assert_(doc1.string == "essai")
        self.assert_(doc1.string2 == "essai2")

        doc2 = Test2(string2="essai")
        self.assert_(doc2.string == "test")

    def testDeleteProperty(self):
        class Test(Document):
            string = StringProperty(default="test")

        doc = Test(string="test")
        del doc.string
        self.assert_(getattr(doc, "string") == None)
        self.assert_(doc['string'] == None)

        class Test2(Document):
            pass

        doc1 = Test2(string="test")
        del doc1.string
        self.assert_(getattr(doc, "string") == None)


    def testContain(self):
        class Test(Document):
            string = StringProperty(default="test")
        doc = Test()
        self.assert_('string' in doc)
        self.assert_('test' not in doc)

        doc.test = "test"
        self.assert_('test' in doc)

    def testLen(self):
        class Test(Document):
            string = StringProperty(default="test")
            string2 = StringProperty()

        doc = Test()
        self.assert_(len(doc) == 3)
        doc.string3 = "4"
        self.assert_(len(doc) == 4)

    def testStore(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            string = StringProperty(default="test")
            string2 = StringProperty()
        Test._db = db

        doc = Test()
        doc.string2 = "test2"

        doc.save()
        self.assert_(doc._id is not None)
        doc1 = db.get(doc._id)
        self.assert_(doc1['string2'] == "test2")

        doc2 = Test(string3="test")
        doc2.save()
        doc3 = db.get(doc2._id)
        self.assert_(doc3['string3'] == "test")

        doc4 = Test(string="doc4")
        db.save_doc(doc4)
        self.assert_(doc4._id is not None)

        self.server.delete_db('couchdbkit_test')

    def testBulkSave(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            string = StringProperty()
        #Test._db = db
        class Test2(Document):
            string = StringProperty()

        doc1 = Test(string="test")
        self.assert_(doc1._id is None)
        doc2 = Test(string="test2")
        self.assert_(doc2._id is None)
        doc3 = Test(string="test3")
        self.assert_(doc3._id is None)

        try:
            Test.bulk_save( [doc1, doc2, doc3] )
        except TypeError, e:
            self.assert_(str(e)== "doc database required to save document" )

        Test.set_db( db )
        bad_doc = Test2(string="bad_doc")
        try:
            Test.bulk_save( [doc1, doc2, doc3, bad_doc] )
        except ValueError, e:
            self.assert_(str(e) == "one of your documents does not have the correct type" )

        Test.bulk_save( [doc1, doc2, doc3] )
        self.assert_(doc1._id is not None)
        self.assert_(doc1._rev is not None)
        self.assert_(doc2._id is not None)
        self.assert_(doc2._rev is not None)
        self.assert_(doc3._id is not None)
        self.assert_(doc3._rev is not None)
        self.assert_(doc1.string == "test")
        self.assert_(doc2.string == "test2")
        self.assert_(doc3.string == "test3")

        doc4 = Test(string="doc4")
        doc5 = Test(string="doc5")
        db.save_docs([doc4, doc5])
        self.assert_(doc4._id is not None)
        self.assert_(doc4._rev is not None)
        self.assert_(doc5._id is not None)
        self.assert_(doc5._rev is not None)
        self.assert_(doc4.string == "doc4")
        self.assert_(doc5.string == "doc5")

        self.server.delete_db('couchdbkit_test')



    def testGet(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            string = StringProperty(default="test")
            string2 = StringProperty()
        Test._db = db

        doc = Test()
        doc.string2 = "test2"
        doc.save()
        doc2 = Test.get(doc._id)

        self.assert_(doc2.string2 == "test2")

        doc2.string3 = "blah"
        doc2.save()
        doc3 = db.get(doc2._id)
        self.assert_(doc3['string3'] == "blah")

        doc4 = db.open_doc(doc2._id, schema=Test)
        self.assert_(isinstance(doc4, Test) == True)
        self.assert_(doc4.string3 == "blah")

        self.server.delete_db('couchdbkit_test')

    def testLoadDynamicProperties(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            pass
        Test._db = db

        doc = Test(field="test",
                field1=datetime.datetime(2008, 11, 10, 8, 0, 0),
                field2=datetime.date(2008, 11, 10),
                field3=datetime.time(8, 0, 0),
                field4=decimal.Decimal("45.4"),
                field5=4.4)
        doc.save()
        doc1 = Test.get(doc._id)
        self.server.delete_db('couchdbkit_test')

        self.assert_(isinstance(doc1.field, basestring))
        self.assert_(isinstance(doc1.field1, datetime.datetime))
        self.assert_(isinstance(doc1.field2, datetime.date))
        self.assert_(isinstance(doc1.field3, datetime.time))
        self.assert_(isinstance(doc1.field4, decimal.Decimal))
        self.assert_(isinstance(doc1.field5, float))

    def testDocType(self):
        class Test(Document):
            string = StringProperty(default="test")

        class Test2(Document):
            string = StringProperty(default="test")

        class Test3(Document):
            doc_type = "test_type"
            string = StringProperty(default="test")

        doc1 = Test()
        doc2 = Test2()
        doc3 = Test2()
        doc4 = Test3()

        self.assert_(doc1._doc_type == 'Test')
        self.assert_(doc1._doc['doc_type'] == 'Test')

        self.assert_(doc3._doc_type == 'Test2')
        self.assert_(doc4._doc_type == 'test_type')
        self.assert_(doc4._doc['doc_type'] == 'test_type')


        db = self.server.create_db('couchdbkit_test')
        Test3._db = Test2._db = Test._db = db

        doc1.save()
        doc2.save()
        doc3.save()
        doc4.save()

        get1 = Test.get(doc1._id)
        get2 = Test2.get(doc2._id)
        get3 = Test2.get(doc3._id)
        get4 = Test3.get(doc4._id)


        self.server.delete_db('couchdbkit_test')
        self.assert_(get1._doc['doc_type'] == 'Test')
        self.assert_(get2._doc['doc_type']== 'Test2')
        self.assert_(get3._doc['doc_type'] == 'Test2')
        self.assert_(get4._doc['doc_type'] == 'test_type')

    def testInheriting(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        class TestDoc2(TestDoc):
            field3 = StringProperty()

        doc = TestDoc2(field1="a", field2="b",
                field3="c")
        doc2 = TestDoc2(field1="a", field2="b",
                field3="c", field4="d")

        self.assert_(len(doc2._dynamic_properties) == 1)

    def testClone(self):
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            a = SchemaProperty(A)
            s1 = StringProperty()

        b = B()
        b.s1 = "test1"
        b.a.s = "test"
        b1 = b.clone()

        self.assert_(b1.s1 == "test1")
        self.assert_('s' in b1._doc['a'])
        self.assert_(b1.a.s == "test")

    def testView(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, doc);
}}"""
                }
            }
        }
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db

        doc.save()
        doc1.save()
        db.save_doc(design_doc)
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 2)
        doc3 = list(results)[0]
        self.assert_(hasattr(doc3, "field1"))
        self.server.delete_db('couchdbkit_test')

    def testMultiWrap(self):
        """
        Tests wrapping of view results to multiple
        classes using a Document class' wrap method
        """

        class A(Document):
            pass
        class B(Document):
            pass

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { emit(doc._id, doc); }"""
                }
            }
        }
        a = A()
        a._id = "1"
        b = B()
        b._id = "2"

        db = self.server.create_db('couchdbkit_test')
        A._db = db
        B._db = db

        a.save()
        b.save()
        db.save_doc(design_doc)
        # provide classes as a list
        results = list(A.view('test/all', classes=[A, B]))
        self.assert_(results[0].__class__ == A)
        self.assert_(results[1].__class__ == B)
        # provide classes as a dict
        results = list(A.view('test/all', classes={'A': A, 'B': B}))
        self.assert_(results[0].__class__ == A)
        self.assert_(results[1].__class__ == B)
        self.server.delete_db('couchdbkit_test')

    def testViewNoneValue(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, null);
}}"""
                }
            }
        }
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db

        doc.save()
        doc1.save()
        db.save_doc(design_doc)
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 2)
        self.assert_(isinstance(results.first(), dict) == True)
        results2 = TestDoc.view('test/all', include_docs=True)
        self.assert_(len(results2) == 2)
        self.assert_(isinstance(results2.first(), TestDoc) == True)
        results3 = TestDoc.view('test/all', include_docs=True,
                                wrapper=lambda row: row['doc']['field1'])
        self.assert_(len(results3) == 2)
        self.assert_(isinstance(results3.first(), unicode) == True)
        self.server.delete_db('couchdbkit_test')

    def test_wrong_doc_type(self):
        db = self.server.create_db('couchdbkit_test')
        try:
            class Foo(Document):
                _db = db
                pass

            class Bar(Foo):
                pass

            Bar().save()

            result = Bar.view('_all_docs', include_docs=True)
            self.assertEqual(len(result), 1)
            bar, = result.all()
            self.assertIsInstance(bar, Bar)

            result = Foo.view('_all_docs', include_docs=True)
            self.assertEqual(len(result), 1)
            result.all()

            from couchdbkit.exceptions import DocTypeError
            result = Foo.view('_all_docs', include_docs=True, classes={
                'Foo': Foo,
            })
            with self.assertRaises(DocTypeError):
                result.all()
        finally:
            self.server.delete_db('couchdbkit_test')

    def testOne(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, doc);
}}"""
                }
            }
        }
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db


        db.save_doc(design_doc)
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 0)
        self.assertRaises(NoResultFound, results.one, except_all=True)
        rst = results.one()
        self.assert_(rst is None)


        results = TestDoc.view('test/all')
        doc.save()
        self.assert_(len(results) == 1)

        one = results.one()
        self.assert_(isinstance(one, TestDoc) == True)

        doc1.save()
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 2)

        self.assertRaises(MultipleResultsFound, results.one)

        self.server.delete_db('couchdbkit_test')

    def testViewStringValue(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, doc.field1);}}"""
                }
            }
        }
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db

        doc.save()
        doc1.save()
        db.save_doc(design_doc)
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 2)
        self.server.delete_db('couchdbkit_test')


    def testTempView(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        design_doc = {
            "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, doc);
}}"""
        }

        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db

        doc.save()
        doc1.save()
        results = TestDoc.temp_view(design_doc)
        self.assert_(len(results) == 2)
        doc3 = list(results)[0]
        self.assert_(hasattr(doc3, "field1"))
        self.server.delete_db('couchdbkit_test')

    def testDocumentAttachments(self):
        db = self.server.create_db('couchdbkit_test')

        class A(Document):
            s = StringProperty(default='test')
            i = IntegerProperty(default=4)
        A._db = db

        a = A()
        a.save()

        text_attachment = u"un texte attaché"
        old_rev = a._rev

        a.put_attachment(text_attachment, "test", "text/plain")
        self.assert_(old_rev != a._rev)
        fetch_attachment = a.fetch_attachment("test")
        self.assert_(text_attachment == fetch_attachment)
        self.server.delete_db('couchdbkit_test')


    def testDocumentDeleteAttachment(self):
        db = self.server.create_db('couchdbkit_test')
        class A(Document):
            s = StringProperty(default='test')
            i = IntegerProperty(default=4)
        A._db = db

        a = A()
        a.save()

        text_attachment = "un texte attaché"

        a.put_attachment(text_attachment, "test", "text/plain")
        a.delete_attachment('test')
        self.assertRaises(ResourceNotFound, a.fetch_attachment, 'test')
        self.assertFalse('test' in a._doc['_attachments'])

        self.server.delete_db('couchdbkit_test')

    def testGetOrCreate(self):
        self.server.create_db('couchdbkit_test')
        db = self.server['couchdbkit_test']

        class A(Document):
            s = StringProperty()
        A._db = db

        def no_exist():
            a = A.get('test')

        self.assertRaises(ResourceNotFound, no_exist)

        a = A.get_or_create('test')
        self.assert_(a._id == "test")

        b = A.get_or_create()
        self.assert_(a._id is not None)
        self.server.delete_db('couchdbkit_test')

    def testBulkDelete(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            string = StringProperty()

        doc1 = Test(string="test")
        doc2 = Test(string="test2")
        doc3 = Test(string="test3")

        Test.set_db(db)
        Test.bulk_save([doc1, doc2, doc3])

        db.bulk_delete([doc1, doc2, doc3])

        print list(db.all_docs(include_docs=True))
        self.assert_(len(db) == 0)
        self.assert_(db.info()['doc_del_count'] == 3)

        self.server.delete_db('couchdbkit_test')


class PropertyTestCase(unittest.TestCase):

    def setUp(self):
        self.server = Server()
        try:
            self.db = self.server.create_db('couchdbkit_test')
        except:
            # waiting we fix all tests use created db
            self.db = self.server['couchdbkit_test']

    def tearDown(self):
        try:
            self.server.delete_db('couchdbkit_test')
        except:
            pass

    def testRequired(self):
        class Test(Document):
            string = StringProperty(required=True)
        Test._db = self.db

        test = Test()
        def ftest():
            test.string = ""
        self.assertRaises(BadValueError, test.save)

    def testRequiredBoolean(self):
        class Test(Document):
            boolean = BooleanProperty(required=True)
        Test._db = self.db

        test = Test()
        test.boolean = False
        test.save()

    def testValidator(self):
        def test_validator(value):
            if value == "test":
                raise BadValueError("test")

        class Test(Document):
            string = StringProperty(validators=test_validator)

        test = Test()
        def ftest():
            test.string = "test"
        self.assertRaises(BadValueError, ftest)

    def testIntegerProperty(self):
        class Test(Document):
            field = IntegerProperty()

        test = Test()
        def ftest():
            test.field = "essai"


        self.assertRaises(BadValueError, ftest)
        test.field = 4
        self.assert_(test._doc['field'] == 4)

    def testDateTimeProperty(self):
        class Test(Document):
            field = DateTimeProperty()

        test = Test()
        def ftest():
            test.field = "essai"

        self.assertRaises(BadValueError, ftest)
        test_dates = [
            ([2008, 11, 10, 8, 0, 0], "2008-11-10T08:00:00Z"),
            ([9999, 12, 31, 23, 59, 59], '9999-12-31T23:59:59Z'),
            ([0001, 1, 1, 0, 0, 1], '0001-01-01T00:00:01Z'),

        ]
        for date, date_str in test_dates:
            test.field = datetime.datetime(*date)
            self.assertEquals(test._doc['field'], date_str)
            value = test.field
            self.assert_(isinstance(value, datetime.datetime))



    def testDateProperty(self):
        class Test(Document):
            field = DateProperty()

        test = Test()
        def ftest():
            test.field = "essai"

        self.assertRaises(BadValueError, ftest)
        test.field = datetime.date(2008, 11, 10)
        self.assert_(test._doc['field'] == "2008-11-10")
        value = test.field
        self.assert_(isinstance(value, datetime.date))


    def testTimeProperty(self):
        class Test(Document):
            field = TimeProperty()

        test = Test()
        def ftest():
            test.field = "essai"

        self.assertRaises(BadValueError, ftest)
        test.field = datetime.time(8, 0, 0)
        self.assert_(test._doc['field'] == "08:00:00")
        value = test.field
        self.assert_(isinstance(value, datetime.time))

    def testMixProperties(self):
        class Test(Document):
            field = StringProperty()
            field1 = DateTimeProperty()

        test = Test(field="test",
                field1 = datetime.datetime(2008, 11, 10, 8, 0, 0))

        self.assert_(test._doc['field'] == "test")
        self.assert_(test._doc['field1'] == "2008-11-10T08:00:00Z")

        self.assert_(isinstance(test.field, basestring))
        self.assert_(isinstance(test.field1, datetime.datetime))
        Test._db = self.db
        test.save()
        doc2 = Test.get(test._id)

        v = doc2.field
        v1 = doc2.field1
        self.assert_(isinstance(v, basestring))
        self.assert_(isinstance(v1, datetime.datetime))

    def testMixDynamicProperties(self):
        class Test(Document):
            field = StringProperty()
            field1 = DateTimeProperty()

        test = Test(field="test",
                field1 = datetime.datetime(2008, 11, 10, 8, 0, 0),
                dynamic_field = 'test')

        Test._db = self.db

        test.save()

        doc2 = Test.get(test._id)

        v1 = doc2.field1
        vd = doc2.dynamic_field

        self.assert_(isinstance(v1, datetime.datetime))
        self.assert_(isinstance(vd, basestring))


    def testSchemaProperty1(self):
        class MySchema(DocumentSchema):
            astring = StringProperty()

        class MyDoc(Document):
            schema = SchemaProperty(MySchema)

        doc = MyDoc()
        self.assert_('schema' in doc._doc)

        doc.schema.astring = u"test"
        self.assert_(doc.schema.astring == u"test")
        self.assert_(doc._doc['schema']['astring'] == u"test")

        MyDoc._db = self.db

        doc.save()
        doc2 = MyDoc.get(doc._id)

        self.assert_(isinstance(doc2.schema, MySchema) == True)
        self.assert_(doc2.schema.astring == u"test")
        self.assert_(doc2._doc['schema']['astring'] == u"test")


    def testSchemaPropertyWithRequired(self):
        class B( Document ):
            class b_schema(DocumentSchema):
                name = StringProperty(  required = True, default = "name" )
            b = SchemaProperty( b_schema )

        B._db = self.db

        b = B()
        self.assertEquals(b.b.name, "name" )

        def bad_value():
            b.b.name = 4
        self.assertRaises(BadValueError, bad_value)

        b1 = B()
        try:
            b1.b.name = 3
            raise RuntimeError
        except BadValueError:
            pass
        b1.b.name = u"test"

    def testSchemaProperty2(self):
        class DocOne(Document):
            name = StringProperty()

        class DocTwo(Document):
            name = StringProperty()
            one = SchemaProperty(DocOne())

        class DocThree(Document):
            name = StringProperty()
            two = SchemaProperty(DocTwo())

        one = DocOne(name='one')
        two = DocTwo(name='two', one=one)
        three = DocThree(name='three', two=two)
        self.assert_(three.two.one.name == 'one')

    def testSchemaPropertyDefault(self):
        class DocOne(DocumentSchema):
            name = StringProperty()

        class DocTwo(Document):
            one = SchemaProperty(DocOne, default=DocOne(name='12345'))

        two = DocTwo()
        self.assert_(two.one.name == '12345')

    def testSchemaPropertyDefault2(self):
        class DocOne(DocumentSchema):
            name = StringProperty()
            field2 = StringProperty(default='54321')

        default_one = DocOne()
        default_one.name ='12345'

        class DocTwo(Document):
            one = SchemaProperty(DocOne, default=default_one)

        two = DocTwo()
        self.assert_(two.one.name == '12345')
        self.assert_(two.one.field2 == '54321')

    def testSchemaPropertyDefault3(self):
        class DocOne(Document):
            name = StringProperty()

        class DocTwo(Document):
            one = SchemaProperty(DocOne, default=DocOne(name='12345'))

        two = DocTwo()
        self.assert_(two.one.name == '12345')

    def testSchemaPropertyDefault4(self):
        class DocOne(Document):
            name = StringProperty()
            field2 = StringProperty(default='54321')

        default_one = DocOne()
        default_one.name ='12345'

        class DocTwo(Document):
            one = SchemaProperty(DocOne, default=default_one)

        two = DocTwo()
        self.assert_(two.one.name == '12345')
        self.assert_(two.one.field2 == '54321')

    def testSchemaWithPythonTypes(self):
        class A(Document):
            c = unicode()
            i = int(4)
        a = A()
        self.assert_(a._doc == {'c': u'', 'doc_type': 'A', 'i': 4})
        def bad_value():
            a.i = "essai"

        self.assertRaises(BadValueError, bad_value)

    def testValueNone(self):
        class A(Document):
            s = StringProperty()
        a = A()
        a.s = None
        self.assert_(a._doc['s'] is None)
        A._db = self.db
        a.save()
        b = A.get(a._id)
        self.assert_(b.s is None)
        self.assert_(b._doc['s'] is None)

    def testSchemaBuild(self):
        schema = DocumentSchema(i = IntegerProperty())
        C = DocumentSchema.build(**schema._dynamic_properties)
        self.assert_('i' in C._properties)
        self.assert_(isinstance(C.i, IntegerProperty))

        c = C()
        self.assert_(c._doc_type == 'AnonymousSchema')
        self.assert_(c._doc == {'doc_type': 'AnonymousSchema', 'i':
            None})


        schema2 = DocumentSchema(i = IntegerProperty(default=-1))
        C3 = DocumentSchema.build(**schema2._dynamic_properties)
        c3 = C3()

        self.assert_(c3._doc == {'doc_type': 'AnonymousSchema', 'i':
            -1})
        self.assert_(c3.i == -1)

        def bad_value():
            c3.i = "test"

        self.assertRaises(BadValueError, bad_value)
        self.assert_(c3.i == -1)

    def testSchemaPropertyValidation2(self):
        class Foo( Document ):
            bar = SchemaProperty(DocumentSchema(foo=IntegerProperty()))

        doc = Foo()
        def bad_value():
            doc.bar.foo = "bla"
        self.assertRaises(BadValueError, bad_value)


    def testDynamicSchemaProperty(self):
        from datetime import datetime
        class A(DocumentSchema):
            s = StringProperty()

        a = A(s="foo")

        class B(Document):
            s1 = StringProperty()
            s2 = StringProperty()
            sm = SchemaProperty(a)

        b = B()
        self.assert_(b._doc == {'doc_type': 'B', 's1': None, 's2': None,
            'sm': {'doc_type': 'A', 's': u'foo'}})

        b.created = datetime(2009, 2, 6, 18, 58, 20, 905556)
        self.assert_(b._doc == {'created': '2009-02-06T18:58:20Z',
            'doc_type': 'B',
            's1': None,
            's2': None,
            'sm': {'doc_type': 'A', 's': u'foo'}})

        self.assert_(isinstance(b.created, datetime) == True)

        a.created = datetime(2009, 2, 6, 20, 58, 20, 905556)
        self.assert_(a._doc ==  {'created': '2009-02-06T20:58:20Z',
            'doc_type': 'A', 's': u'foo'})

        self.assert_(b._doc == {'created': '2009-02-06T18:58:20Z',
            'doc_type': 'B',
            's1': None,
            's2': None,
            'sm': {'created': '2009-02-06T20:58:20Z', 'doc_type': 'A',
            's': u'foo'}})


        b2 = B()
        b.s1 = "t1"

        self.assert_(b2.sm._doc == b.sm._doc)
        self.assert_(b.s1 != b2.s1)

        b2.sm.s3 = "t2"
        self.assert_(b2.sm.s3 == b.sm.s3)
        self.assert_(b.s1 != b2.s1)

        b.sm.s3 = "t3"
        self.assert_(b2.sm.s3 == "t3")

    def testStaticSchemaProperty(self):
        from datetime import datetime
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            s1 = StringProperty()
            s2 = StringProperty()
            sm = SchemaProperty(A)

        b = B()
        self.assert_(b._doc == {'doc_type': 'B', 's1': None, 's2': None,
            'sm': {'doc_type': 'A', 's': None}})

        b.sm.s = "t1"
        self.assert_(b._doc == {'doc_type': 'B', 's1': None, 's2': None,
            'sm': {'doc_type': 'A', 's': u't1'}})

        b2 = B()
        self.assert_(b2._doc == {'doc_type': 'B', 's1': None, 's2':
            None, 'sm': {'doc_type': 'A', 's': None}})

        b2.sm.s = "t2"
        self.assert_(b2._doc == {'doc_type': 'B', 's1': None, 's2':
            None, 'sm': {'doc_type': 'A', 's': u't2'}})

        self.assert_(b2.sm.s != b.sm.s)

    def testSchemaListProperty(self):
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        self.assert_(b.slm == [])

        a = A()
        a.s = "test"
        b.slm.append(a)
        self.assert_(b._doc == {'doc_type': 'B', 'slm': [{'doc_type': 'A', 's': u'test'}]})
        a1 = A()
        a1.s = "test2"
        b.slm.append(a1)
        self.assert_(b._doc == {'doc_type': 'B', 'slm': [{'doc_type': 'A', 's': u'test'}, {'doc_type': 'A', 's': u'test2'}]})

        B.set_db(self.db)
        b.save()
        b1 = B.get(b._id)
        self.assert_(len(b1.slm) == 2)
        self.assert_(b1.slm[0].s == "test")


    def testSchemaListPropertySlice(self):
        """SchemaListProperty slice methods
        """
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        a3 = A()
        a3.s = 'test3'
        b.slm[0:1] = [a1, a2]
        self.assertEqual(len(b.slm), 2)
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a1.s, a2.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)},
                    {'doc_type': 'A', 's': unicode(a2.s)}]
        })
        b.slm.append(a3)
        c = b.slm[1:3]
        self.assertEqual(len(c), 2)
        self.assertEqual([c[0].s, c[1].s], [a2.s, a3.s])
        del b.slm[1:3]
        self.assertEqual(len(b.slm), 1)
        self.assertEqual(b.slm[0].s, a1.s)
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)}]
        })


    def testSchemaListPropertyContains(self):
        """SchemaListProperty contains method
        """
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        b.slm = [a1]
        self.assertTrue(a1 in b.slm)
        self.assertFalse(a2 in b.slm)


    def testSchemaListPropertyCount(self):
        """SchemaListProperty count method
        """
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        b.slm = [a1, a2, a1]
        self.assertEqual(b.slm.count(a1), 2)


    def testSchemaListPropertyExtend(self):
        """SchemaListProperty extend method
        """
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        b.slm.extend([a1, a2])
        self.assertEqual(len(b.slm), 2)
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a1.s, a2.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)},
                    {'doc_type': 'A', 's': unicode(a2.s)}]
        })


    def testSchemaListPropertyIndex(self):
        """SchemaListProperty index method
        """
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        a3 = A()
        a3.s = 'test3'
        b.slm = [a1, a2, a1, a2, a1]
        self.assertEqual(b.slm.index(a1), 0)
        self.assertEqual(b.slm.index(a2, 2), 3)
        self.assertEqual(b.slm.index(a1, 1, 3), 2)
        self.assertEqual(b.slm.index(a1, 1, -2), 2)
        with self.assertRaises(ValueError) as cm:
            b.slm.index(a3)
        self.assertEqual(str(cm.exception), 'list.index(x): x not in list')


    def testSchemaListPropertyInsert(self):
        """SchemaListProperty insert method
        """
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        a3 = A()
        a3.s = 'test3'
        b.slm = [a1, a3]
        b.slm.insert(1, a2)
        self.assertEqual(len(b.slm), 3)
        self.assertEqual(
            [b.slm[0].s, b.slm[1].s, b.slm[2].s], [a1.s, a2.s, a3.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)},
                    {'doc_type': 'A', 's': unicode(a2.s)},
                    {'doc_type': 'A', 's': unicode(a3.s)}]
        })


    def testSchemaListPropertyPop(self):
        """SchemaListProperty pop method
        """
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        a3 = A()
        a3.s = 'test3'
        b.slm = [a1, a2, a3]
        v = b.slm.pop()
        self.assertEqual(v.s, a3.s)
        self.assertEqual(len(b.slm), 2)
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a1.s, a2.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)},
                    {'doc_type': 'A', 's': unicode(a2.s)}]
        })
        v = b.slm.pop(0)
        self.assertEqual(v.s, a1.s)
        self.assertEqual(len(b.slm), 1)
        self.assertEqual(b.slm[0].s, a2.s)
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a2.s)}]
        })


    def testSchemaListPropertyRemove(self):
        """SchemaListProperty remove method
        """
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        b.slm = [a1, a2]
        b.slm.remove(a1)
        self.assertEqual(len(b.slm), 1)
        self.assertEqual(b.slm[0].s, a2.s)
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a2.s)}]
        })
        with self.assertRaises(ValueError) as cm:
            b.slm.remove(a1)
        self.assertEqual(str(cm.exception), 'list.remove(x): x not in list')


    def testSchemaListPropertyReverse(self):
        """SchemaListProperty reverse method
        """
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        b.slm = [a1, a2]
        b.slm.reverse()
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a2.s, a1.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a2.s)},
                    {'doc_type': 'A', 's': unicode(a1.s)}]
        })


    def testSchemaListPropertySort(self):
        """SchemaListProperty sort method
        """
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        b.slm = [a2, a1]
        b.slm.sort(key=lambda item: item['s'])
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a1.s, a2.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)},
                    {'doc_type': 'A', 's': unicode(a2.s)}]
        })
        b.slm.sort(key=lambda item: item['s'], reverse=True)
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a2.s, a1.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a2.s)},
                    {'doc_type': 'A', 's': unicode(a1.s)}]
        })
        b.slm.sort(cmp=lambda x, y: cmp(x['s'].lower(), y['s'].lower()))
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a1.s, a2.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)},
                    {'doc_type': 'A', 's': unicode(a2.s)}]
        })


    def testSchemaDictProperty(self):
        class A(DocumentSchema):
            i = IntegerProperty()

        class B(Document):
            d = SchemaDictProperty(A)

        a1 = A()
        a1.i = 123
        self.assert_(a1._doc == {'i': 123, 'doc_type': 'A'})

        a2 = A()
        a2.i = 42
        self.assert_(a2._doc == {'i': 42, 'doc_type': 'A'})

        b = B()
        b.d['v1'] = a1
        b.d[23]   = a2
        self.assert_(b._doc == {'doc_type': 'B', 'd': {"v1": {'i': 123, 'doc_type': 'A'}, '23': {'i': 42, 'doc_type': 'A'}}})

        b.set_db(self.db)
        b.save()

        b1 = B.get(b._id)
        self.assert_(len(b1.d) == 2)
        self.assert_(b1.d['v1'].i == 123)
        self.assert_(b1.d[23].i == 42)


    def testListProperty(self):
        from datetime import datetime
        class A(Document):
            l = ListProperty(datetime)
        A.set_db(self.db)

        # we can save an empty list
        a = A()
        self.assert_(a._doc == {'doc_type': 'A', 'l': []})
        a.save()
        self.assert_(a['_id'])
        self.assert_(a['l']==[])

        a = A()
        d = datetime(2009, 4, 13, 22, 56, 10, 967388)
        a.l.append(d)
        self.assert_(len(a.l) == 1)
        self.assert_(a.l[0] == datetime(2009, 4, 13, 22, 56, 10))
        self.assert_(a._doc == {'doc_type': 'A', 'l': ['2009-04-13T22:56:10Z']})
        a.l.append({ 's': "test"})
        self.assert_(a.l == [datetime(2009, 4, 13, 22, 56, 10), {'s': 'test'}])
        self.assert_(a._doc == {'doc_type': 'A', 'l': ['2009-04-13T22:56:10Z', {'s': 'test'}]}
        )

        a.save()

        b = A.get(a._id)
        self.assert_(len(b.l) == 2)
        self.assert_(b.l[0] == datetime(2009, 4, 13, 22, 56, 10))
        self.assert_(b._doc['l'] == ['2009-04-13T22:56:10Z', {'s': 'test'}])


        a = A(l=["a", "b", "c"])
        a.save()
        b = self.db.get(a._id, wrapper=A.wrap)
        self.assert_(a.l == ["a", "b", "c"])
        b.l = []
        self.assert_(b.l == [])
        self.assert_(b.to_json()['l'] == [])


    def testListPropertyNotEmpty(self):
        from datetime import datetime
        class A(Document):
            l = ListProperty(datetime, required=True)

        a = A()
        self.assert_(a._doc == {'doc_type': 'A', 'l': []})
        self.assertRaises(BadValueError, a.save)
        try:
            a.validate()
        except BadValueError, e:
            pass
        self.assert_(str(e) == 'Property l is required.')

        d = datetime(2009, 4, 13, 22, 56, 10, 967388)
        a.l.append(d)
        self.assert_(len(a.l) == 1)
        self.assert_(a.l[0] == datetime(2009, 4, 13, 22, 56, 10))
        self.assert_(a._doc == {'doc_type': 'A', 'l': ['2009-04-13T22:56:10Z']})
        a.validate()

        class A2(Document):
            l = ListProperty()

        a2 = A2()
        self.assertTrue(a2.validate(required=False))
        self.assertTrue(a2.validate())


    def testListPropertyWithType(self):
        from datetime import datetime
        class A(Document):
            l = ListProperty(item_type=datetime)
        a = A()
        a.l.append("test")
        self.assertRaises(BadValueError, a.validate)

        class B(Document):
            ls = StringListProperty()
        b = B()
        b.ls.append(u"test")
        self.assertTrue(b.validate())
        b.ls.append(datetime.utcnow())
        self.assertRaises(BadValueError, b.validate)

        b1  = B()
        b1.ls = [u'hello', u'123']
        self.assert_(b1.ls == [u'hello', u'123'])
        self.assert_(b1._doc['ls'] == [u'hello', u'123'])

        self.assert_(b1.ls.index(u'hello') == 0)
        b1.ls.remove(u'hello')
        self.assert_(u'hello' not in b1.ls)


    def testListPropertyExtend(self):
        """list extend method for property w/o type
        """
        class A(Document):
            l = ListProperty()

        a = A()
        a.l.extend([42, 24])
        self.assert_(a.l == [42, 24])
        self.assert_(a._doc == {'doc_type': 'A', 'l': [42, 24]})


    def testListPropertyExtendWithType(self):
        """list extend method for property w/ type
        """
        from datetime import datetime
        class A(Document):
            l = ListProperty(item_type=datetime)

        a = A()
        d1 = datetime(2011, 3, 11, 21, 31, 1)
        d2 = datetime(2011, 11, 3, 13, 12, 2)
        a.l.extend([d1, d2])
        self.assert_(a.l == [d1, d2])
        self.assert_(a._doc == {
            'doc_type': 'A',
            'l': ['2011-03-11T21:31:01Z', '2011-11-03T13:12:02Z']
        })


    def testListPropertyInsert(self):
        """list insert method for property w/o type
        """
        class A(Document):
            l = ListProperty()

        a = A()
        a.l = [42, 24]
        a.l.insert(1, 4224)
        self.assertEqual(a.l, [42, 4224, 24])
        self.assertEqual(a._doc, {'doc_type': 'A', 'l': [42, 4224, 24]})


    def testListPropertyInsertWithType(self):
        """list insert method for property w/ type
        """
        from datetime import datetime
        class A(Document):
            l = ListProperty(item_type=datetime)

        a = A()
        d1 = datetime(2011, 3, 11, 21, 31, 1)
        d2 = datetime(2011, 11, 3, 13, 12, 2)
        d3 = datetime(2010, 1, 12, 3, 2, 3)
        a.l = [d1, d3]
        a.l.insert(1, d2)
        self.assertEqual(a.l, [d1, d2, d3])
        self.assertEqual(a._doc, {
            'doc_type': 'A',
            'l': ['2011-03-11T21:31:01Z',
                  '2011-11-03T13:12:02Z',
                  '2010-01-12T03:02:03Z']
        })


    def testListPropertyPop(self):
        """list pop method for property w/o type
        """
        class A(Document):
            l = ListProperty()

        a = A()
        a.l = [42, 24, 4224]
        v = a.l.pop()
        self.assert_(v == 4224)
        self.assert_(a.l == [42, 24])
        self.assert_(a._doc == {'doc_type': 'A', 'l': [42, 24]})
        v = a.l.pop(0)
        self.assert_(v == 42)
        self.assert_(a.l == [24])
        self.assert_(a._doc == {'doc_type': 'A', 'l': [24]})


    def testListPropertyPopWithType(self):
        """list pop method for property w/ type
        """
        from datetime import datetime
        class A(Document):
            l = ListProperty(item_type=datetime)

        a = A()
        d1 = datetime(2011, 3, 11, 21, 31, 1)
        d2 = datetime(2011, 11, 3, 13, 12, 2)
        d3 = datetime(2010, 1, 12, 3, 2, 3)
        a.l = [d1, d2, d3]
        v = a.l.pop()
        self.assertEqual(v, d3)
        self.assertEqual(a.l, [d1, d2])


    def testDictProperty(self):
        from datetime import datetime
        class A(Document):
            d = DictProperty()
        A.set_db(self.db)

        a = A()
        self.assert_(a._doc == {'d': {}, 'doc_type': 'A'})
        a.d['s'] = 'test'
        self.assert_(a._doc == {'d': {'s': 'test'}, 'doc_type': 'A'})
        a.d['created'] = datetime(2009, 4, 16, 16, 5, 41)
        self.assert_(a._doc == {'d': {'created': '2009-04-16T16:05:41Z', 's': 'test'}, 'doc_type': 'A'})
        self.assert_(isinstance(a.d['created'], datetime) == True)
        a.d.update({'s2': 'test'})
        self.assert_(a.d['s2'] == 'test')
        a.d.update({'d2': datetime(2009, 4, 16, 16, 5, 41)})
        self.assert_(a._doc['d']['d2'] == '2009-04-16T16:05:41Z')
        self.assert_(a.d['d2'] == datetime(2009, 4, 16, 16, 5, 41))
        self.assert_(a.d == {'s2': 'test', 's': 'test', 'd2': datetime(2009, 4, 16, 16, 5, 41), 'created': datetime(2009, 4, 16, 16, 5, 41)})

        a = A()
        a.d['test'] = { 'a': datetime(2009, 5, 10, 21, 19, 21, 127380) }
        self.assert_(a.d == { 'test': {'a': datetime(2009, 5, 10, 21, 19, 21)}})
        self.assert_(a._doc == {'d': {'test': {'a': '2009-05-10T21:19:21Z'}}, 'doc_type': 'A'} )

        a.d['test']['b'] = "essai"
        self.assert_(a._doc == {'d': {'test': {'a': '2009-05-10T21:19:21Z', 'b': 'essai'}}, 'doc_type': 'A'})

        a.d['essai'] = "test"
        self.assert_(a.d == {'essai': 'test',
         'test': {'a': datetime(2009, 5, 10, 21, 19, 21),
                  'b': 'essai'}}
        )
        self.assert_(a._doc == {'d': {'essai': 'test', 'test': {'a': '2009-05-10T21:19:21Z', 'b': 'essai'}},
         'doc_type': 'A'})

        del a.d['test']['a']
        self.assert_(a.d == {'essai': 'test', 'test': {'b': 'essai'}})
        self.assert_(a._doc ==  {'d': {'essai': 'test', 'test': {'b': 'essai'}}, 'doc_type': 'A'})

        a.d['test']['essai'] = { "a": datetime(2009, 5, 10, 21, 21, 11) }
        self.assert_(a.d == {'essai': 'test',
         'test': {'b': 'essai',
                  'essai': {'a': datetime(2009, 5, 10, 21, 21, 11)}}}
        )
        self.assert_(a._doc == {'d': {'essai': 'test',
               'test': {'b': 'essai', 'essai': {'a': '2009-05-10T21:21:11Z'}}},
         'doc_type': 'A'}
        )

        del a.d['test']['essai']
        self.assert_(a._doc == {'d': {'essai': 'test', 'test': {'b': 'essai'}}, 'doc_type': 'A'})

        a = A()
        a.d['s'] = "level1"
        a.d['d'] = {}
        a.d['d']['s'] = "level2"
        self.assert_(a._doc == {'d': {'d': {'s': 'level2'}, 's': 'level1'}, 'doc_type': 'A'})
        a.save()
        a1 = A.get(a._id)
        a1.d['d']['s'] = "level2 edited"
        self.assert_(a1.d['d']['s'] == "level2 edited")
        self.assert_(a1._doc['d']['d']['s'] == "level2 edited")

    def testDictPropertyNotEmpty(self):
        from datetime import datetime
        class A(Document):
            d = DictProperty(required=True)
        A.set_db(self.db)

        a = A()
        self.assert_(a._doc == {'doc_type': 'A', 'd': {}})
        self.assertRaises(BadValueError, a.save)
        try:
            a.save()
        except BadValueError, e:
            pass
        self.assert_(str(e) == 'Property d is required.')

        d = datetime(2009, 4, 13, 22, 56, 10, 967388)
        a.d['date'] = d
        self.assert_(a.d['date'] == datetime(2009, 4, 13, 22, 56, 10))
        self.assert_(a._doc == {'doc_type': 'A', 'd': { 'date': '2009-04-13T22:56:10Z' }})
        a.save()

        class A2(Document):
            d = DictProperty()
        a2 = A2()
        self.assertTrue(a2.validate(required=False))
        self.assertTrue(a2.validate())

    def testDynamicDictProperty(self):
        from datetime import datetime
        class A(Document):
            pass

        a = A()
        a.d = {}

        a.d['test'] = { 'a': datetime(2009, 5, 10, 21, 19, 21, 127380) }
        self.assert_(a.d == {'test': {'a': datetime(2009, 5, 10, 21, 19, 21, 127380)}})
        self.assert_(a._doc == {'d': {'test': {'a': '2009-05-10T21:19:21Z'}}, 'doc_type': 'A'} )

        a.d['test']['b'] = "essai"
        self.assert_(a._doc == {'d': {'test': {'a': '2009-05-10T21:19:21Z', 'b': 'essai'}}, 'doc_type': 'A'})

        a.d['essai'] = "test"
        self.assert_(a.d == {'essai': 'test',
         'test': {'a': datetime(2009, 5, 10, 21, 19, 21, 127380),
                  'b': 'essai'}}
        )
        self.assert_(a._doc == {'d': {'essai': 'test', 'test': {'a': '2009-05-10T21:19:21Z', 'b': 'essai'}},
         'doc_type': 'A'})

        del a.d['test']['a']
        self.assert_(a.d == {'essai': 'test', 'test': {'b': 'essai'}})
        self.assert_(a._doc ==  {'d': {'essai': 'test', 'test': {'b': 'essai'}}, 'doc_type': 'A'})

        a.d['test']['essai'] = { "a": datetime(2009, 5, 10, 21, 21, 11, 425782) }
        self.assert_(a.d == {'essai': 'test',
         'test': {'b': 'essai',
                  'essai': {'a': datetime(2009, 5, 10, 21, 21, 11, 425782)}}}
        )
        self.assert_(a._doc == {'d': {'essai': 'test',
               'test': {'b': 'essai', 'essai': {'a': '2009-05-10T21:21:11Z'}}},
         'doc_type': 'A'}
        )

        del a.d['test']['essai']
        self.assert_(a._doc == {'d': {'essai': 'test', 'test': {'b': 'essai'}}, 'doc_type': 'A'})

    def testDynamicDictProperty2(self):
        from datetime import datetime
        class A(Document):
            pass

        A.set_db(self.db)

        a = A()
        a.s = "test"
        a.d = {}
        a.d['s'] = "level1"
        a.d['d'] = {}
        a.d['d']['s'] = "level2"
        self.assert_(a._doc == {'d': {'d': {'s': 'level2'}, 's': 'level1'}, 'doc_type': 'A', 's': u'test'})
        a.save()

        a1 = A.get(a._id)
        a1.d['d']['s'] = "level2 edited"
        self.assert_(a1.d['d']['s'] == "level2 edited")

        self.assert_(a1._doc['d']['d']['s'] == "level2 edited")

        class A2(Document):
            pass
        A2.set_db(self.db)
        a = A2(l=["a", "b", "c"])
        a.save()
        b = self.db.get(a._id, wrapper=A2.wrap)
        self.assert_(b.l == ["a", "b", "c"])
        b.l = []
        self.assert_(b.l == [])
        self.assert_(b.to_json()['l'] == [])

    def testDictPropertyPop(self):
        class A(Document):
            x = DictProperty()

        a = A()
        self.assert_(a.x.pop('nothing', None) == None)

    def testDictPropertyPop2(self):
        class A(Document):
            x = DictProperty()

        a = A()
        a.x['nothing'] = 'nothing'
        self.assert_(a.x.pop('nothing') == 'nothing')
        self.assertRaises(KeyError, a.x.pop, 'nothing')

    def testDynamicListProperty(self):
        from datetime import datetime
        class A(Document):
            pass

        A.set_db(self.db)

        a = A()
        a.l = []
        a.l.append(1)
        a.l.append(datetime(2009, 5, 12, 13, 35, 9, 425701))
        a.l.append({ 's': "test"})
        self.assert_(a.l == [1, datetime(2009, 5, 12, 13, 35, 9, 425701), {'s': 'test'}])
        self.assert_(a._doc == {'doc_type': 'A', 'l': [1, '2009-05-12T13:35:09Z', {'s': 'test'}]}
        )
        a.l[2]['date'] = datetime(2009, 5, 12, 13, 35, 9, 425701)
        self.assert_(a._doc == {'doc_type': 'A',
         'l': [1,
               '2009-05-12T13:35:09Z',
               {'date': '2009-05-12T13:35:09Z', 's': 'test'}]}
        )
        a.save()

        a1 = A.get(a._id)
        self.assert_(a1.l == [1,
         datetime(2009, 5, 12, 13, 35, 9),
         {u'date': datetime(2009, 5, 12, 13, 35, 9), u's': u'test'}]
        )

        a.l[2]['s'] = 'test edited'
        self.assert_(a.l == [1,
         datetime(2009, 5, 12, 13, 35, 9, 425701),
         {'date': datetime(2009, 5, 12, 13, 35, 9, 425701),
          's': 'test edited'}]
        )
        self.assert_(a._doc['l'] == [1,
         '2009-05-12T13:35:09Z',
         {'date': '2009-05-12T13:35:09Z', 's': 'test edited'}]
        )


        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "A") { emit(doc._id, doc);
}}"""
                }
            }
        }
        self.db.save_doc(design_doc)

        a2 = A()
        a2.l = []
        a2.l.append(7)
        a2.save()
        docs = A.view('test/all')
        self.assert_(len(docs) == 2)

        a3 = A()
        a3.l = []
        a3.save()
        docs = A.view('test/all')
        self.assert_(len(docs) == 3)

        a = A(l = [1, 2])
        self.assert_(a.l == [1,2])
        self.assert_(a._doc['l'] == [1,2])

        a = A()
        a.l = [1, 2]
        self.assert_(a.l == [1,2])
        self.assert_(a._doc['l'] == [1,2])


        class A2(Document):
            pass
        A2.set_db(self.db)
        a = A2(d={"a": 1, "b": 2, "c": 3})
        a.save()
        b = self.db.get(a._id, wrapper=A2.wrap)
        self.assert_(b.d == {"a": 1, "b": 2, "c": 3})
        b.d = {}
        self.assert_(b.d == {})
        self.assert_(b.to_json()['d'] == {})



if support_setproperty:
    class SetPropertyTestCase(unittest.TestCase):
        def testSetPropertyConstructor(self):
            """SetProperty constructor including default & item_type args
            """
            class A(Document):
                s = SetProperty()
            class B(Document):
                s = SetProperty(default=set((42, 24)))

            a = A()
            self.assertEqual(a._doc, {'doc_type': 'A', 's': []})
            b = B()
            self.assertEqual(b._doc['doc_type'], 'B')
            self.assertItemsEqual(b._doc['s'], [42, 24])
            with self.assertRaises(ValueError) as cm:
                class C(Document):
                    s = SetProperty(item_type=tuple)
            self.assertIn(
                "item_type <type 'tuple'> not in set([", str(cm.exception))


        def testSetPropertyAssignment(self):
            """SetProperty value assignment, len, in & not in
            """
            class A(Document):
                s = SetProperty()

            a = A()
            a.s = set(('foo', 'bar'))
            self.assertEqual(a.s, set(('foo', 'bar')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'bar'])
            self.assertEqual(len(a.s), 2)
            self.assertEqual(len(a._doc['s']), 2)
            self.assertIn('foo', a.s)
            self.assertIn('foo', a._doc['s'])
            self.assertNotIn('baz', a.s)
            self.assertNotIn('baz', a._doc['s'])


        def testSetPropertyAssignmentWithType(self):
            """SetProperty value assignment, len, in & not in w/ type
            """
            from datetime import datetime
            class A(Document):
                s = SetProperty(item_type=datetime)

            d1 = datetime(2011, 3, 15, 17, 8, 1)
            a = A()
            a.s = set((d1, ))
            self.assertEqual(a.s, set((d1, )))
            self.assertItemsEqual(a._doc['s'], ['2011-03-15T17:08:01Z'])
            self.assertEqual(len(a.s), 1)
            self.assertEqual(len(a._doc['s']), 1)
            self.assertIn(d1, a.s)
            self.assertIn('2011-03-15T17:08:01Z', a._doc['s'])
            self.assertNotIn(datetime(2011, 3, 16, 10, 37, 2), a.s)
            self.assertNotIn('2011-03-16T10:37:02Z', a._doc['s'])


        def testSetPropertySubSuperDisjoint(self):
            """SetProperty Python subset, superset & disjoint operators work
            """
            class A(Document):
                s = SetProperty()

            iter1 = ('foo', 'bar')
            a = A()
            a.s = set(iter1)
            self.assertTrue(a.s.issubset(iter1))
            self.assertTrue(a.s <= set(iter1))
            iter2 = ('foo', 'bar', 'baz')
            self.assertTrue(a.s < set(iter2))
            self.assertTrue(a.s.issuperset(iter1))
            self.assertTrue(a.s >= set(iter1))
            iter2 = ('foo', )
            self.assertTrue(a.s > set(iter2))
            iter2 = ('bam', 'baz')
            self.assertTrue(a.s.isdisjoint(iter2))


        def testSetPropertyUnionIntersectionDifferences(self):
            """SetProperty Python union, intersection & differences operators work
            """
            class A(Document):
                s = SetProperty()

            iter1 = ('foo', 'bar')
            iter2 = ('bar', 'baz')
            iter3 = ('bar', 'fiz')
            a = A()
            a.s = set(iter1)
            # Union
            b = a.s.union(iter2)
            self.assertEqual(b, set(('foo', 'bar', 'baz')))
            b = a.s.union(iter2, iter3)
            self.assertEqual(b, set(('foo', 'bar', 'baz', 'fiz')))
            b = a.s | set(iter2)
            self.assertEqual(b, set(('foo', 'bar', 'baz')))
            b = a.s | set(iter2) | set(iter3)
            self.assertEqual(b, set(('foo', 'bar', 'baz', 'fiz')))
            # Intersection
            b = a.s.intersection(iter2)
            self.assertEqual(b, set(('bar', )))
            b = a.s.intersection(iter2, iter3)
            self.assertEqual(b, set(('bar', )))
            b = a.s & set(iter2)
            self.assertEqual(b, set(('bar', )))
            b = a.s & set(iter2) & set(iter3)
            self.assertEqual(b, set(('bar', )))
            # Difference
            b = a.s.difference(iter2)
            self.assertEqual(b, set(('foo', )))
            b = a.s.difference(iter2, iter3)
            self.assertEqual(b, set(('foo', )))
            b = a.s - set(iter2)
            self.assertEqual(b, set(('foo', )))
            b = a.s - set(iter2) - set(iter3)
            self.assertEqual(b, set(('foo', )))
            # Symmetric difference
            self.assertEqual(a.s.symmetric_difference(iter2), set(('foo', 'baz')))
            self.assertEqual(a.s ^ set(iter2), set(('foo', 'baz')))


        def testSetPropertyCopy(self):
            """SetProperty Python shallow copy method works
            """
            class A(Document):
                s = SetProperty()

            a = A()
            a.s = set(('foo', 'bar'))
            b = a.s.copy()
            self.assertIsNot(b, a.s)


        def testSetPropertyUpdate(self):
            """SetProperty update method keeps Python set & _doc list in sync
            """
            class A(Document):
                s = SetProperty()

            iter1 = ('foo', 'bar')
            iter2 = ('bar', 'baz')
            iter3 = ('baz', 'fiz')
            a = A()
            a.s = set(iter1)
            a.s.update(iter1)
            self.assertEqual(a.s, set(('foo', 'bar')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'bar'])
            a.s = set(iter1)
            a.s.update(iter2)
            self.assertEqual(a.s, set(('foo', 'bar', 'baz')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'baz'])
            a.s = set(iter1)
            a.s.update(iter2, iter3)
            self.assertEqual(a.s, set(('foo', 'bar', 'baz', 'fiz')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'baz', 'fiz'])
            a.s = set(iter1)
            a.s |= set(iter2)
            self.assertEqual(a.s, set(('foo', 'bar', 'baz')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'baz'])
            a.s = set(iter1)
            a.s |= set(iter2) | set(iter3)
            self.assertEqual(a.s, set(('foo', 'bar', 'baz', 'fiz')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'baz', 'fiz'])


        def testSetPropertyIntersectionUpdate(self):
            """SetProperty intersection_update method keeps Python & _doc in sync
            """
            class A(Document):
                s = SetProperty()

            iter1 = ('foo', 'baz')
            iter2 = ('bar', 'baz')
            iter3 = ('bar', 'fiz')
            a = A()
            a.s = set(iter1)
            a.s.intersection_update(iter1)
            self.assertEqual(a.s, set(('foo', 'baz')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'baz'])
            a.s = set(iter1)
            a.s.intersection_update(iter2)
            self.assertEqual(a.s, set(('baz', )))
            self.assertItemsEqual(a._doc['s'], ['baz'])
            a.s = set(iter1)
            a.s.intersection_update(iter2, iter3)
            self.assertEqual(a.s, set())
            self.assertItemsEqual(a._doc['s'], [])
            a.s = set(iter1)
            a.s &= set(iter2)
            self.assertEqual(a.s, set(('baz', )))
            self.assertItemsEqual(a._doc['s'], ['baz'])
            a.s = set(iter1)
            a.s &= set(iter2) & set(iter3)
            self.assertEqual(a.s, set())
            self.assertItemsEqual(a._doc['s'], [])


        def testSetPropertyDifferenceUpdate(self):
            """SetProperty difference_update method keeps Python & _doc in sync
            """
            class A(Document):
                s = SetProperty()

            iter1 = ('foo', 'baz', 'fiz')
            iter2 = ('bar', 'baz')
            iter3 = ('bar', 'fiz')
            a = A()
            a.s = set(iter1)
            a.s.difference_update(iter1)
            self.assertEqual(a.s, set())
            self.assertEqual(a._doc['s'], [])
            a.s = set(iter1)
            a.s.difference_update(iter2)
            self.assertEqual(a.s, set(('foo', 'fiz')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'fiz'])
            a.s = set(iter1)
            a.s.difference_update(iter2, iter3)
            self.assertEqual(a.s, set(('foo', )))
            self.assertItemsEqual(a._doc['s'], ['foo'])
            a.s = set(iter1)
            a.s -= set(iter1)
            self.assertEqual(a.s, set())
            self.assertEqual(a._doc['s'], [])
            a.s = set(iter1)
            a.s -= set(iter2)
            self.assertEqual(a.s, set(('foo', 'fiz')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'fiz'])
            a.s = set(iter1)
            a.s -= set(iter2) | set(iter3)
            self.assertEqual(a.s, set(('foo', )))
            self.assertItemsEqual(a._doc['s'], ['foo'])


        def testSetPropertySymmetricDifferenceUpdate(self):
            """SetProperty difference_update method keeps Python & _doc in sync
            """
            class A(Document):
                s = SetProperty()

            iter1 = ('foo', 'baz', 'fiz')
            iter2 = ('bar', 'baz')
            a = A()
            a.s = set(iter1)
            a.s.symmetric_difference_update(iter1)
            self.assertEqual(a.s, set())
            self.assertEqual(a._doc['s'], [])
            a.s = set(iter1)
            a.s.symmetric_difference_update(iter2)
            self.assertEqual(a.s, set(('foo', 'bar', 'fiz')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'fiz'])
            a.s = set(iter1)
            a.s ^= set(iter1)
            self.assertEqual(a.s, set())
            self.assertEqual(a._doc['s'], [])
            a.s = set(iter1)
            a.s ^= set(iter2)
            self.assertEqual(a.s, set(('foo', 'bar', 'fiz')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'fiz'])


        def testSetPropertyAdd(self):
            """SetProperty add method works
            """
            class A(Document):
                s = SetProperty()

            a = A()
            a.s = set(('foo', 'bar'))
            a.s.add('bar')
            self.assertEqual(a.s, set(('foo', 'bar')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'bar'])
            a.s.add('baz')
            self.assertEqual(a.s, set(('foo', 'bar', 'baz')))
            self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'baz'])


        def testSetPropertyRemove(self):
            """SetProperty remove method works
            """
            class A(Document):
                s = SetProperty()

            a = A()
            a.s = set(('foo', 'bar'))
            a.s.remove('foo')
            self.assertEqual(a.s, set(('bar', )))
            self.assertItemsEqual(a._doc['s'], ['bar'])
            with self.assertRaises(KeyError):
                a.s.remove('foo')


        def testSetPropertyDiscard(self):
            """SetProperty discard method works
            """
            class A(Document):
                s = SetProperty()

            a = A()
            a.s = set(('foo', 'bar'))
            a.s.discard('foo')
            self.assertEqual(a.s, set(('bar', )))
            self.assertItemsEqual(a._doc['s'], ['bar'])
            a.s.discard('foo')
            self.assertEqual(a.s, set(('bar', )))
            self.assertItemsEqual(a._doc['s'], ['bar'])


        def testSetPropertyPop(self):
            """SetProperty pop method works
            """
            class A(Document):
                s = SetProperty()

            a = A()
            a.s = set(('foo', 'bar'))
            b = a.s.pop()
            self.assertNotIn(b, a.s)
            self.assertNotIn(b, a._doc['s'])
            b = a.s.pop()
            self.assertNotIn(b, a.s)
            self.assertNotIn(b, a._doc['s'])
            with self.assertRaises(KeyError):
                a.s.pop()


        def testSetPropertyClear(self):
            """SetProperty clear method works
            """
            class A(Document):
                s = SetProperty()

            a = A()
            a.s = set(('foo', 'bar'))
            a.s.clear()
            self.assertEqual(a.s, set())
            self.assertEqual(a._doc['s'], [])



class SchemaProxyUtilityTestCase(unittest.TestCase):
    def test_svalue_to_json_instance(self):
        from couchdbkit.schema.properties_proxy import svalue_to_json

        svalue_to_json({}, Document(), True)

    def test_svalue_to_json_schema(self):
        from couchdbkit.schema.properties_proxy import svalue_to_json

        svalue_to_json({}, Document, False)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
