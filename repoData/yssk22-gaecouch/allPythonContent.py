__FILENAME__ = errors
class HttpError(Exception):
    def __init__(self, status = 500, 
                 error = 'unknown error', 
                 reason = 'uknown'):
        self._status = status
        self._error = error
        self._reason = reason

    @property
    def status(self): 
        return self._status
    
    @property
    def error(self):
        return self._error
    
    @property
    def reason(self):
        return self._reason

class NotImplemented(HttpError):
    def __init__(self, error = 'not_implemented', reason = 'please contribute implementation.'):
        super(NotImplemented, self).__init__(501, error = error, reason = reason)

class BadRequest(HttpError):
    def __init__(self, error = 'bad_request', reason = 'bad_request'):
        super(BadRequest, self).__init__(400, error = error, reason = reason)

class NotFound(HttpError):
    def __init__(self, error = 'not_found', reason = 'not_found'):
        super(NotFound, self).__init__(404, error = error, reason = reason)

class Conflict(HttpError):
    def __init__(self, error = 'conflict', reason = 'conflict'):
        super(Conflict, self).__init__(409, error = error, reason = reason)

class PreconditionFailed(HttpError):
    def __init__(self, error, reason):
        super(PreconditionFailed, self).__init__(412, error, reason)

########NEW FILE########
__FILENAME__ = base

########NEW FILE########
__FILENAME__ = config
from couch.handlers import BaseHandler

class Config(BaseHandler):
    pass

########NEW FILE########
__FILENAME__ = database
import logging
from google.appengine.ext import webapp
from google.appengine.ext import db
from django.utils import simplejson as json
from couch.handlers import BaseHandler
from couch import models
from couch import errors

class AllDBs(BaseHandler):
    def get(self):
        q = models.Database.all()
        list = [l.key().name() for l in q]
        self.writeln(list)

class Database(BaseHandler):
    ''' database handler 
    '''
    def get(self, dbname):
        ''' GET /{dbname} : Get database info. '''
        database = models.Database.get_by_key_name(dbname)
        if database:
            self.writeln(database)
        else:
            raise errors.NotFound('no_db_file')

    def post(self, dbname):
        database = models.Database.get_by_key_name(dbname)
        if not database:
            raise errors.NotFound('no_db_file')
        try:
            document = json.loads(self.request.body)
        except ValueError, e:
            logging.info(e)
            raise errors.BadRequest(reason = 'invalid UTF-8 JSON')
        document = database.save(document)
        self.writeln({ 'ok' : True,
                       'id' : document.id,
                       'rev' : document.rev })

    def put(self, dbname):
        ''' PUT /{dbname} : Create a database. '''
        def _trans():
            database = models.Database.get_by_key_name(dbname)
            if database:
                raise errors.PreconditionFailed(error = "file_exists",
                                                reason = "The database could not be created, the file already exists.")
            database = models.Database(key_name= dbname)
            database.put()

        db.run_in_transaction(_trans)
        self.writeln({'ok': True})

    def delete(self, dbname):
        ''' DELETE /{dbname} : Delete a database '''
        def _trans():
            database = models.Database.get_by_key_name(dbname)
            if database:
                # TODO: all related document entities should be deleted.
                database.delete()
            else:
                raise errors.NotFound('missing')
        db.run_in_transaction(_trans)
        self.writeln({'ok': True})

########NEW FILE########
__FILENAME__ = document
import logging
from google.appengine.ext import webapp
from google.appengine.ext import db
from django.utils import simplejson as json
from couch.handlers import BaseHandler
from couch import models
from couch import errors

class _BaseHandler(BaseHandler):
    ''' Base Handler for Document APIs '''
    def _database(self, dbname):
        database = models.Database.get_by_key_name(dbname)
        if not database:
            raise errors.NotFound('no_db_file')
        return database

    def _document(self, database, id):
        document = database.get(id)
        if not document:
            raise errors.NotFound(reason = 'missing')
        if document.deleted:
            raise errors.NotFound(reason = 'deleted')
        return document

class BulkDocs(_BaseHandler):
    def post(self, dbname):
        ''' GET /{dbname}/{id} : Update a document. '''
        database = self._database(dbname)
        try:
            document = json.loads(self.request.body)
        except ValueError, e:
            logging.info(self.request.body)
            raise errors.BadRequest(reason = 'invalid UTF-8 JSON')
        docs = document['docs']
        all_or_nothing = document.get('all_or_nothing', False)
        entities = database.bulk_save(docs, all_or_nothing = all_or_nothing)
        ret = [{'id': e.id , 'rev': e.rev} for e in entities]
        self.writeln(ret)

class Document(_BaseHandler):
    def put(self, dbname, id):
        ''' GET /{dbname}/{id} : Update a document. '''
        database = self._database(dbname)
        try:
            document = json.loads(self.request.body)
        except ValueError:
            raise errors.BadRequest(reason = 'invalid UTF-8 JSON')
        
        document["_id"] = id
        document = database.save(database, document)
        self.writeln({ 'ok' : True,
                       'id' : document.id,
                       'rev' : document.rev })

    def get(self, dbname, id):
        ''' GET /{dbname}/{id} : Get a document. '''
        database = self._database(dbname)
        document = self._document(database, id)
        self.writeln(document) # TODO passed to_dict options

    def delete(self, dbname, id):
        ''' DELETE /{dbname}/{id} : Delete a document. '''
        database = self._database(dbname)
        rev = self.request.get('rev', None)
        document = {'_id' : id, '_rev': rev, '_deleted': True}
        document = database.save(database, document)
        self.writeln({ 'ok' : True,
                       'id' : document.id,
                       'rev' : document.rev })
        
class DesignDocument(_BaseHandler):
    pass

class Attachment(_BaseHandler):
    pass


########NEW FILE########
__FILENAME__ = misc
''' Provides misc handlers
'''
from couch.handlers import BaseHandler
from couch import models
from couch import errors

class Welcome(BaseHandler):
    def get(self):
        ''' GET / '''
        self.writeln({
                'couchdb' : "Welcome",
                'version' : '0.11.0'
                })

class Uuids(BaseHandler):
    def get(self):
        ''' GET /_uuids{?count=N} '''
        try:
            count = int(self.request.get('count', '1'))
            if count < 0:
                raise errors.HttpError(reason = 'function_clause')
            self.writeln({'uuids': models.gen_uuid(count)})
        except ValueError:
            raise errors.HttpError(reason = 'badarg')

class Replicate(BaseHandler):
    pass

class Stats(BaseHandler):
    pass

class Session(BaseHandler):
    pass

class ActiveTasks(BaseHandler):
    pass

########NEW FILE########
__FILENAME__ = database
import time
import hashlib
from datetime import datetime
from google.appengine.ext import db
from django.utils import simplejson as json
from couch.models.document import Document, DocumentRoot
from couch.models.util import *

class Database(db.Model):
    # CouchDB properties
    disk_format_version = db.IntegerProperty(default = 5)
    update_seq = db.IntegerProperty(default = 0)
    purge_seq = db.IntegerProperty(default = 0)
    doc_count = db.IntegerProperty(default = 0)
    doc_del_count = db.IntegerProperty(default = 0)
    compact_running = db.BooleanProperty(default = False)
    instance_start_time = db.DateTimeProperty(auto_now_add = True)
    disk_size = db.IntegerProperty(default = 0)

    def to_dict(self):
        dict = {}
        dict['db_name'] = self.key().name()
        for (key, prop) in self.properties().items():
            val = prop.get_value_for_datastore(self)
            if isinstance(val, datetime):
                val = time.mktime(val.timetuple())
            dict[key] = val
        return dict

    def save(self, raw_document):
        ''' save the raw document and returns Document entity'''
        return self._save(raw_document)

    def bulk_save(self, raw_docs, all_or_nothing = False):
        ''' save bulk documents and returns a list of Document entities'''
        return [self.save(raw_doc) for raw_doc in raw_docs]

    @property
    def dbname(self):
        ''' Returns the database name '''
        return self.key().name()

    def _save(self, document):
        if document.has_key('_id'):
            id = document.get('_id')
            del document['_id']
        else:
            id = gen_uuid()[0]
        
        if document.has_key('_rev'):
            rev = document.get('_rev')
            del document['_rev']
        else:
            rev = None

        if document.has_key('_deleted'):
            deleted = document.get('_deleted') == True
            del document['_deleted']
        else:
            deleted = False

        docstring = json.dumps(document)
        return db.run_in_transaction(self._save_doc_transaction, id, rev, deleted, document, docstring)
    
    
    def _save_doc_transaction(self, id, rev, deleted, document, docstring):
        dbname = self.dbname
        # get current document
        docroot = DocumentRoot.get_by_key_name("%s/%s" % (dbname, id))
        if not docroot:
            docroot = DocumentRoot(key_name = "%s/%s" % (dbname, id))

        if docroot.deleted:
            raise errors.NotFound(reason = 'deleted')

        if docroot.revno > 0:
            if not rev:
                raise errors.Conflict(reason = 'Document update conflict.')
            try:
                revno, revsuffix = rev.split('-')
            except ValueError:
                raise errors.BadRequest(reason = 'Invalid rev format')
            if docroot.revno != int(revno) or docroot.revsuffix != revsuffix:
                raise errors.Conflict(reason = 'Document update conflict.')
            

        # save the docroot and document entity
        docroot.revno = docroot.revno + 1
        docroot.revsuffix = hashlib.md5(docstring).hexdigest()
        docroot.deleted = deleted

        document['_id'] = id
        document['_rev'] = docroot.rev()

        entity = Document(parent = docroot)
        entity.id = document['_id']
        entity.rev = document['_rev']
        entity.dbname = dbname
        entity.deleted = deleted
        entity.docstring = json.dumps(document) # use pickle?

        docroot.put()
        entity.put()
        return entity

    def get(self, id):
        GQL = 'SELECT * FROM Document WHERE dbname = :1 AND id = :2 ORDER BY rev DESC'
        query = db.GqlQuery(GQL, self.key().name(), id)
        return query.get()

########NEW FILE########
__FILENAME__ = document
from datetime import datetime
from google.appengine.ext import db
from django.utils import simplejson as json
from couch import errors
from couch.models.util import gen_uuid

class DocumentRoot(db.Model):
    ''' Controls document '''
    revno = db.IntegerProperty(default = 0)
    revsuffix = db.StringProperty()
    deleted = db.BooleanProperty(default = False)

    def rev(self):
        return '%s-%s' % (self.revno, self.revsuffix)

class Document(db.Model):
    id = db.StringProperty()
    rev = db.StringProperty()
    dbname = db.StringProperty()
    docstring = db.TextProperty()
    deleted = db.BooleanProperty(default = False)

    def to_dict(self):
        return json.loads(self.docstring)

########NEW FILE########
__FILENAME__ = model

########NEW FILE########
__FILENAME__ = util
import uuid

def gen_uuid(count = 1):
    # TODO: support uuid1 and sequencial uuid
    return [''.join(uuid.uuid4().__str__().split('-')) for i in range(count)]

########NEW FILE########
__FILENAME__ = dispatch
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import couch.handlers
import couch.handlers.database
import couch.handlers.document
import couch.handlers.misc
import couch.handlers.config

application = webapp.WSGIApplication(
    [(r'/', couch.handlers.misc.Welcome),
     (r'/_all_dbs', couch.handlers.database.AllDBs),
     (r'/_active_tasks', couch.handlers.misc.ActiveTasks),
     (r'/_config/?',  couch.handlers.config.Config),
     (r'/_config/([^/]+)/?', couch.handlers.config.Config),
     (r'/_config/([^/]+)/([^/]+)/?', couch.handlers.config.Config),
     (r'/_uuids',     couch.handlers.misc.Uuids),
     (r'/_replicate', couch.handlers.misc.Replicate),
     (r'/_stats', couch.handlers.misc.Stats),
     (r'/_session',  couch.handlers.misc.Session),
     (r'/([^/]+)/?', couch.handlers.database.Database),
     (r'/([^/]+)/_bulk_docs', couch.handlers.document.BulkDocs),
     (r'/([^/]+)/_design/([^/]+)/?', couch.handlers.document.DesignDocument),
     (r'/([^/]+)/([^/]+)/?', couch.handlers.document.Document)],
    debug=True)

def main():
    run_wsgi_app(application)


########NEW FILE########
