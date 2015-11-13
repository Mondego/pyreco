__FILENAME__ = collection
from bibserver.core import current_user
from bibserver.config import config

def read(account, collection):
    return True

def update(account, collection):
    allowed = not account.is_anonymous() and collection["owner"] == account.id
    if not account.is_anonymous():
        try:
            if account.id in collection['_admins']:
                allowed = True
        except:
            pass
        if account.id in config['super_user']:
            allowed = True
    return allowed

def create(account, collection):
    return not account.is_anonymous()


########NEW FILE########
__FILENAME__ = user
from bibserver.core import current_user
from bibserver.config import config

def update(account, user):
    allowed = not account.is_anonymous() and user.id == account.id
    if not account.is_anonymous():
        if account.id in config['super_user']:
            allowed = True
    return allowed

def is_super(account):
    return not account.is_anonymous() and account.id in config['super_user']

########NEW FILE########
__FILENAME__ = config
import os
import json

'''read the config.json file and make available as a config dict'''

def load_config(path):
    fileobj = open(path)
    c = ""
    for line in fileobj:
        if line.strip().startswith("#"):
            continue
        else:
            c += line
    out = json.loads(c)

    # add some critical defaults if necessary
    if 'facet_field' not in out:
        out['facet_field'] = ''

    return out

here = os.path.dirname(__file__)
parent = os.path.dirname(here)
config_path = os.path.join(parent, 'config.json')
config = load_config(config_path)

if os.path.exists(os.path.join(parent, 'local_config.json')):
    local_config = load_config(os.path.join(parent, 'local_config.json'))
    config.update(local_config)

__all__ = ['config']


''' wrap a config dict in a class if required'''

class Config(object):
    def __init__(self,confdict=config):
        '''Create Configuration object from a configuration dictionary.'''
        self.cfg = confdict
        
    def __getattr__(self, attr):
        return self.cfg.get(attr, None)
        



########NEW FILE########
__FILENAME__ = core
import os
from flask import Flask

from bibserver import default_settings
from flask.ext.login import LoginManager, current_user
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    configure_app(app)
    setup_error_email(app)
    login_manager.setup_app(app)
    return app

def configure_app(app):
    app.config.from_object(default_settings)
    # parent directory
    here = os.path.dirname(os.path.abspath( __file__ ))
    config_path = os.path.join(os.path.dirname(here), 'app.cfg')
    if os.path.exists(config_path):
        app.config.from_pyfile(config_path)

def setup_error_email(app):
    ADMINS = app.config.get('ADMINS', '')
    if not app.debug and ADMINS:
        import logging
        from logging.handlers import SMTPHandler
        mail_handler = SMTPHandler('127.0.0.1',
                                   'server-error@no-reply.com',
                                   ADMINS, 'error')
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

app = create_app()


########NEW FILE########
__FILENAME__ = dao
# this is the data access layer
import json
import uuid
import UserDict
import httplib
import urllib
from datetime import datetime
import hashlib

import pyes
from werkzeug import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin

from bibserver.config import config
import bibserver.util, bibserver.auth


def make_id(data):
    '''Create a new id for data object based on a hash of the data representation
    Ignore the _last_modified, _created fields
    ##TODO Ignore ALL fields that startswith _
    '''
    if '_id' in data: return data['_id']
    new_data = {}
    for k,v in data.items():
        if k in ('_last_modified', '_created'): continue
        new_data[k] = v
    buf = json.dumps(new_data, sort_keys=True)
    new_id = hashlib.md5(buf).hexdigest()
    return new_id
    
    
def init_db():
    conn, db = get_conn()
    try:
        conn.create_index(db)
    except:
        pass
    mappings = config["mappings"]
    for mapping in mappings:
        host = str(config['ELASTIC_SEARCH_HOST']).rstrip('/')
        db_name = config['ELASTIC_SEARCH_DB']
        fullpath = '/' + db_name + '/' + mapping + '/_mapping'
        c =  httplib.HTTPConnection(host)
        c.request('GET', fullpath)
        result = c.getresponse()
        if result.status == 404:
            print mapping
            c =  httplib.HTTPConnection(host)
            c.request('PUT', fullpath, json.dumps(mappings[mapping]))
            res = c.getresponse()
            print res.read()


def get_conn():
    host = str(config["ELASTIC_SEARCH_HOST"])
    db_name = config["ELASTIC_SEARCH_DB"]
    conn = pyes.ES([host])
    return conn, db_name

class InvalidDAOIDException(Exception):
    pass
    
class DomainObject(UserDict.IterableUserDict):
    # set __type__ on inheriting class to determine elasticsearch object
    __type__ = None

    def __init__(self, **kwargs):
        '''Initialize a domain object with key/value pairs of attributes.
        '''
        # IterableUserDict expects internal dictionary to be on data attribute
        if '_source' in kwargs:
            self.data = dict(kwargs['_source'])
            self.meta = dict(kwargs)
            del self.meta['_source']
        else:
            self.data = dict(kwargs)

    @property
    def id(self):
        '''Get id of this object.'''
        return self.data.get('_id', None)
        
    @property
    def version(self):
        return self.meta.get('_version', None)

    def save(self):
        '''Save to backend storage.'''
        # TODO: refresh object with result of save
        return self.upsert(self.data)

    def delete(self):
        url = str(config['ELASTIC_SEARCH_HOST'])
        loc = config['ELASTIC_SEARCH_DB'] + "/" + self.__type__ + "/" + self.id
        conn = httplib.HTTPConnection(url)
        conn.request('DELETE', loc)
        resp = conn.getresponse()
        return ''

    @classmethod
    def get(cls, id_):
        '''Retrieve object by id.'''
        if id_ is None:
            return None
        conn, db = get_conn()
        try:
            out = conn.get(db, cls.__type__, id_)
            return cls(**out)
        except pyes.exceptions.ElasticSearchException, inst:
            if inst.status == 404:
                return None
            else:
                raise

    @classmethod
    def get_mapping(cls):
        conn, db = get_conn()
        return conn.get_mapping(cls.__type__, db)
        
    @classmethod
    def get_facets_from_mapping(cls,mapping=False,prefix=''):
        # return a sorted list of all the keys in the index
        if not mapping:
            mapping = cls.get_mapping()[cls.__type__]['properties']
        keys = []
        for item in mapping:
            if mapping[item].has_key('fields'):
                for item in mapping[item]['fields'].keys():
                    if item != 'exact' and not item.startswith('_'):
                        keys.append(prefix + item + config['facet_field'])
            else:
                keys = keys + cls.get_facets_from_mapping(mapping=mapping[item]['properties'],prefix=prefix+item+'.')
        keys.sort()
        return keys
        
    @classmethod
    def upsert(cls, data, state=None):
        '''Update backend object with a dictionary of data.

        If no id is supplied an uuid id will be created before saving.
        '''
        conn, db = get_conn()
        cls.bulk_upsert([data], state)
        conn.flush_bulk()

        # TODO: should we really do a cls.get() ?
        return cls(**data)

    @classmethod
    def bulk_upsert(cls, dataset, state=None):
        '''Bulk update backend object with a list of dicts of data.
        If no id is supplied an uuid id will be created before saving.'''
        conn, db = get_conn()
        for data in dataset:
            if not type(data) is dict: continue
            if '_id' in data:
                id_ = data['_id'].strip()
            else:
                id_ = make_id(data)
                data['_id'] = id_
            
            if '_created' not in data:
                data['_created'] = datetime.now().strftime("%Y%m%d%H%M%S")
            data['_last_modified'] = datetime.now().strftime("%Y%m%d%H%M%S")
            
            index_result = conn.index(data, db, cls.__type__, urllib.quote_plus(id_), bulk=True)
        # refresh required after bulk index
        conn.refresh()
    
    @classmethod
    def delete_by_query(cls, query):
        url = str(config['ELASTIC_SEARCH_HOST'])
        loc = config['ELASTIC_SEARCH_DB'] + "/" + cls.__type__ + "/_query?q=" + urllib.quote_plus(query)
        conn = httplib.HTTPConnection(url)
        conn.request('DELETE', loc)
        resp = conn.getresponse()
        return resp.read()

    @classmethod
    def query(cls, q='', terms=None, facet_fields=None, flt=False, default_operator='AND', **kwargs):
        '''Perform a query on backend.

        :param q: maps to query_string parameter.
        :param terms: dictionary of terms to filter on. values should be lists.
        :param kwargs: any keyword args as per
            http://www.elasticsearch.org/guide/reference/api/search/uri-request.html
        '''
        conn, db = get_conn()
        if not q:
            ourq = pyes.query.MatchAllQuery()
        else:
            if flt:
                ourq = pyes.query.FuzzyLikeThisQuery(like_text=q,**kwargs)
            else:
                ourq = pyes.query.StringQuery(q, default_operator=default_operator)
        if terms:
            for term in terms:
                if isinstance(terms[term],list):
                    for val in terms[term]:
                        termq = pyes.query.TermQuery(term, val)
                        ourq = pyes.query.BoolQuery(must=[ourq,termq])
                else:
                    termq = pyes.query.TermQuery(term, terms[term])
                    ourq = pyes.query.BoolQuery(must=[ourq,termq])

        ourq = ourq.search(**kwargs)
        if facet_fields:
            for item in facet_fields:
                ourq.facet.add_term_facet(item['key'], size=item.get('size',100), order=item.get('order',"count"))
        out = conn.search(ourq, db, cls.__type__)
        return out

    @classmethod
    def raw_query(self, query_string):
        host = str(config['ELASTIC_SEARCH_HOST']).rstrip('/')
        db_path = config['ELASTIC_SEARCH_DB']
        fullpath = '/' + db_path + '/' + self.__type__ + '/_search' + '?' + query_string
        c = httplib.HTTPConnection(host)
        c.request('GET', fullpath)
        result = c.getresponse()
        # pass through the result raw
        return result.read()


class Record(DomainObject):
    __type__ = 'record'


class Note(DomainObject):
    __type__ = 'note'

    @classmethod
    def about(cls, id_):
        '''Retrieve notes by id of record they are about'''
        if id_ is None:
            return None
        conn, db = get_conn()
        res = Note.query(terms={"about":id_})
        return [i['_source'] for i in res['hits']['hits']]


class Collection(DomainObject):
    __type__ = 'collection'

    @property
    def records(self):
        size = Record.query(terms={'owner':self['owner'],'collection':self['collection']})['hits']['total']
        if size != 0:
            res = [Record.get(i['_source']['_id']) for i in Record.query(terms={'owner':self['owner'],'collection':self['collection']},size=size)['hits']['hits']]
        else: res = []
        return res

    @classmethod
    def get_by_owner_coll(cls,owner,coll):
        res = cls.query(terms={'owner':owner,'collection':coll})
        if res['hits']['total'] == 1:
            return cls(**res['hits']['hits'][0]['_source'])
        else:
            return None
            
    def delete(self):
        url = str(config['ELASTIC_SEARCH_HOST'])
        loc = config['ELASTIC_SEARCH_DB'] + "/" + self.__type__ + "/" + self.id
        print loc
        conn = httplib.HTTPConnection(url)
        conn.request('DELETE', loc)
        resp = conn.getresponse()
        print resp.read()
        for record in self.records:
            record.delete()
    
    def __len__(self):
        res = Record.query(terms={'owner':self['owner'],'collection':self['collection']})
        return res['hits']['total']

    
class Account(DomainObject, UserMixin):
    __type__ = 'account'

    def set_password(self, password):
        self.data['password'] = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.data['password'], password)

    @property
    def is_super(self):
        return bibserver.auth.user.is_super(self)
    
    @property
    def collections(self):
        colls = Collection.query(terms={
            'owner': [self.id]
            })
        colls = [ Collection(**item['_source']) for item in colls['hits']['hits'] ]
        return colls
        
    @property
    def notes(self):
        res = Note.query(terms={
            'owner': [self.id]
        })
        allnotes = [ Note(**item['_source']) for item in res['hits']['hits'] ]
        return allnotes
        
    def delete(self):
        url = str(config['ELASTIC_SEARCH_HOST'])
        loc = config['ELASTIC_SEARCH_DB'] + "/" + self.__type__ + "/" + self.id
        conn = httplib.HTTPConnection(url)
        conn.request('DELETE', loc)
        resp = conn.getresponse()
        for coll in self.collections:
            coll.delete()
        for note in self.notes:
            note.delete()


########NEW FILE########
__FILENAME__ = default_settings
SECRET_KEY = 'default-key'


########NEW FILE########
__FILENAME__ = importer
# the data import manager
# gets an uploaded file or retrieves a file from a URL
# indexes the records found in the file by upserting via the DAO
import urllib2
import re
from cStringIO import StringIO
import unicodedata
import uuid
import json

import bibserver.dao
import bibserver.util as util
from bibserver.config import config

class Importer(object):
    def __init__(self, owner, requesturl=False):
        self.owner = owner
        self.requesturl = requesturl

    def upload(self, fileobj, collection=None):
        '''Import a bibjson collection into the database.
       
        :param fileobj: a fileobj pointing to file from which to import
        collection records (and possibly collection metadata)
        :param collection: collection dict for use when creating collection. If
        undefined collection must be extractable from the fileobj.

        :return: same as `index` method.
        '''
        jsonin = json.load(fileobj)
        metadata = jsonin.get('metadata',False)
        record_dicts = jsonin.get('records', jsonin)

        # if metadata provided from file, roll it into the collection object
        if metadata:
            metadata.update(collection)
            collection = metadata
        
        return self.index(collection, record_dicts)
    
    def index(self, collection_dict, record_dicts):
        '''Add this collection and its records to the database index.
        :return: (collection, records) tuple of collection and associated
        record objects.
        '''
        col_label_slug = util.slugify(collection_dict['label'])
        collection = bibserver.dao.Collection.get_by_owner_coll(self.owner.id, col_label_slug)
        if not collection:
            collection = bibserver.dao.Collection(**collection_dict)
            assert 'label' in collection, 'Collection must have a label'
            if not 'collection' in collection:
                collection['collection'] = col_label_slug
            collection['owner'] = self.owner.id

        collection.save()

        for rec in record_dicts:
            if not type(rec) is dict: continue
            rec['owner'] = collection['owner']
            if 'collection' in rec:
                if collection['collection'] != rec['collection']:
                    rec['collection'] = collection['collection']
            else:
                rec['collection'] = collection['collection']
            if not self.requesturl and 'SITE_URL' in config:
                self.requesturl = str(config['SITE_URL'])
            if self.requesturl:
                if not self.requesturl.endswith('/'):
                    self.requesturl += '/'
                if '_id' not in rec:
                    rec['_id'] = bibserver.dao.make_id(rec)
                rec['url'] = self.requesturl + collection['owner'] + '/' + collection['collection'] + '/'
                if 'id' in rec:
                    rec['url'] += rec['id']
                elif '_id' in rec:
                    rec['url'] += rec['_id']
        bibserver.dao.Record.bulk_upsert(record_dicts)
        return collection, record_dicts

def findformat(filename):
    if filename.endswith(".json"): return "json"
    if filename.endswith(".bibtex"): return "bibtex"
    if filename.endswith(".bib"): return "bibtex"
    if filename.endswith(".csv"): return "csv"
    return "bibtex"


########NEW FILE########
__FILENAME__ = ingest
'''
Independent running process.
Handling uploads asynchronously.
See: https://github.com/okfn/bibserver/wiki/AsyncUploadDesign
'''

import os, stat, sys, uuid, time
import subprocess
from cStringIO import StringIO
import requests
import hashlib
import json
from datetime import datetime
import traceback
import bibserver.dao
from bibserver.config import config
from bibserver.importer import Importer
from bibserver.core import app
import bibserver.util as util
from flask import render_template, make_response, abort, send_from_directory, redirect, request

# Constant used to track installed plugins
PLUGINS = {}

class IngestTicketInvalidOwnerException(Exception):
    pass
class IngestTicketInvalidInit(Exception):
    pass
class IngestTicketInvalidId(Exception):
    pass
    
class IngestTicket(dict):
    def __init__(self,*args,**kwargs):        
        'Creates a new Ingest Ticket, ready for processing by the ingest pipeline'
        if '_id' not in kwargs:
            kwargs['_id'] = uuid.uuid4().hex
        if 'state' not in kwargs:
            kwargs['state'] = 'new'
        if '_created' not in kwargs:
            kwargs['_created'] = time.time()
        owner = kwargs.get('owner')
        if not type(owner) in (str, unicode):
            raise IngestTicketInvalidOwnerException()
        for x in ('collection', 'format'):
            if not kwargs.get(x):
                raise IngestTicketInvalidInit('You need to supply the parameter %s' % x)
        for x in ('_created', '_last_modified'):
            if x in kwargs:
                kwargs[x] = datetime.fromtimestamp(kwargs[x])
        dict.__init__(self,*args,**kwargs)
    
    @classmethod
    def load(cls, ticket_id):
        filename = os.path.join(config['download_cache_directory'], ticket_id)  + '.ticket'
        if not os.path.exists(filename):
            raise IngestTicketInvalidId(ticket_id)
        data = json.loads(open(filename).read())
        return cls(**data)
        
    def save(self):
        self['_last_modified'] = time.time()
        self['_created'] = time.mktime(self['_created'].timetuple())
        filename = os.path.join(config['download_cache_directory'], self['_id'])  + '.ticket'
        open(filename, 'wb').write(json.dumps(self))
        for x in ('_created', '_last_modified'):
            self[x] = datetime.fromtimestamp(self[x])
        
    def fail(self, msg):
        self['state'] = 'failed'
        err = (datetime.now().strftime("%Y%m%d%H%M"), msg)
        self.setdefault('exception', []).append(err)
        self.save()

    def delete(self):
        filename = os.path.join(config['download_cache_directory'], self['_id'])  + '.ticket'
        os.remove(filename)
        
    def __unicode__(self):
        try:
            return u'%s/%s,%s [%s] - %s' % (self['owner'], self['collection'], self['format'], self['state'], self['_last_modified'])
        except:
            return repr(self)
        
    def __str__(self):
        return unicode(self).encode('utf8')
        
    @property
    def id(self):
        return self['_id']

def index(ticket):
    ticket['state'] = 'populating_index'
    ticket.save()
    # Make sure the parsed content is in the cache
    download_cache_directory = config['download_cache_directory']
    in_path = os.path.join(download_cache_directory, ticket['data_json'])
    if not os.path.exists(in_path):
        ticket.fail('Parsed content for %s not found' % in_path)
        return
    data = open(in_path).read()
    if len(data) < 1:
        raise Exception('The parsed data in this ticket is empty.' )
    
    # TODO check for metadata section to update collection from this?
    owner = bibserver.dao.Account.get(ticket['owner'])
    importer = Importer(owner=owner)
    collection = {
        'label': ticket['collection'],
        'collection': util.slugify(ticket['collection']),
        'description': ticket.get('description'),
        'source': ticket['source_url'],
        'format': ticket['format'],
        'license': ticket.get('license', u"Not specified"),
    }
    collection, records = importer.upload(open(in_path), collection)
    ticket['state'] = 'done'
    ticket.save()
    
def parse(ticket):
    ticket['state'] = 'parsing'
    ticket.save()
    if 'data_md5' not in ticket:
        ticket.fail('Attempt to parse ticket, but no data_md5 found')
        return
    p = PLUGINS.get(ticket['format'])
    if not p:
        ticket.fail('Parser plugin for format %s not found' % ticket['format'])
        return
    # Make sure the downloaded content is in the cache
    download_cache_directory = config['download_cache_directory']
    in_path = os.path.join(download_cache_directory, ticket['data_md5'])
    if not os.path.exists(in_path):
        ticket.fail('Downloaded content for %s not found' % in_path)
        return
    p = subprocess.Popen(p['_path'], shell=True, stdin=open(in_path), stdout=subprocess.PIPE, stderr=subprocess.PIPE)    
    data = p.stdout.read()
    md5sum = hashlib.md5(data).hexdigest()
    download_cache_directory = config['download_cache_directory']    
    out_path = os.path.join(download_cache_directory, md5sum)
    open(out_path, 'wb').write(data)
    
    ticket['data_json'] = md5sum
    if ticket.get('only_parse') == True:
        ticket['state'] = 'done'
    else:
        ticket['state'] = 'parsed'
    # Check if there is any data in the stderr of the parser
    # If so, add it to the ticket as potential feedback
    data_stderr = p.stderr.read()
    if len(data_stderr) > 0:
        ticket['parse_feedback'] = data_stderr
    ticket.save()
    
def store_data_in_cache(data):
    md5sum = hashlib.md5(data).hexdigest()
    download_cache_directory = config['download_cache_directory']
    out_path = os.path.join(download_cache_directory, md5sum)
    if not os.path.exists(out_path):
        open(out_path, 'wb').write(data)
    return md5sum
    
def download(ticket):
    ticket['state'] = 'downloading'
    ticket.save()
    p = PLUGINS.get(ticket['format'])
    if p and p.get('downloads'):
        data = ticket['source_url'].strip()
        content_type = 'text/plain'
    else:
        url = ticket['source_url'].strip()
        r = requests.get(url)
        content_type = r.headers['content-type']
        r.raise_for_status()
        data = r.content
        if len(data) < 1:
            ticket.fail('Data is empty, HTTP status code %s ' % r.status_code)
            return
        
    ticket['data_md5'] = store_data_in_cache(data)
    ticket['data_content_type'] = content_type

    ticket['state'] = 'downloaded'
    ticket.save()
    
    
def determine_action(ticket):
    'For the given ticket determine what the next action to take is based on the state'
    try:
        state = ticket['state']
        print ticket['state'], ticket['_id'],
        if state == 'new':
            download(ticket)
        if state == 'downloaded':
            parse(ticket)
        if state == 'parsed':
            index(ticket)
    except:
        ## TODO
        # For some reason saving the traceback to the ticket here is not saving the exception
        # The ticket does not record the 'failed' state, and remains in eg. a 'downloading' state
        ticket.fail(traceback.format_exc())
    print '...', ticket['state']

def get_tickets(state=None):
    "Get tickets with the given state"
    buf = []
    for f in os.listdir(config['download_cache_directory']):
        if f.endswith('.ticket'):
            t = IngestTicket.load(f[:-7])
            if not state or (state == t['state']):
                buf.append(t)
    return buf
    
def scan_parserscrapers(directory):
    "Scan the specified directory for valid parser/scraper executables"
    found = []
    for root, dirs, files in os.walk(directory):
        for name in files:
            filename = os.path.join(root, name)
            is_ex = stat.S_IXUSR & os.stat(filename)[stat.ST_MODE]            
            if is_ex:
                # Try and call this executable with a -bibserver to get a config
                try:
                    output = subprocess.check_output(filename+' -bibserver', shell=True)
                    output_json = json.loads(output)
                    if output_json['bibserver_plugin']:
                        output_json['_path'] = filename
                        found.append(output_json)
                except subprocess.CalledProcessError:
                    sys.stderr.write(traceback.format_exc())
                except ValueError:
                    sys.stderr.write('Error parsing plugin output:\n')
                    sys.stderr.write(output)
    return found

def get_plugins():
    filename = os.path.join(config.get('parserscrapers_plugin_directory'), 'plugins.json')
    return json.loads(open(filename).read())
    
def init():
    for d in ('download_cache_directory', 'parserscrapers_plugin_directory'):
        dd = config.get(d)
        if not os.path.exists(dd):
            os.mkdir(dd)

    # Scan for available parser/scraper plugins
    parserscrapers_plugin_directory = config.get('parserscrapers_plugin_directory')
    if not parserscrapers_plugin_directory:
        sys.stderr.write('Error: parserscrapers_plugin_directory config entry not found\n')
    plugins = scan_parserscrapers(parserscrapers_plugin_directory)
    if plugins:
        for ps in plugins:
            PLUGINS[ps['format']] = ps
    filename = os.path.join(config.get('parserscrapers_plugin_directory'), 'plugins.json')
    open(filename, 'w').write(json.dumps(PLUGINS))

def run():
    last_flash = time.time() - 500
    count = 0
    running = True
    while running:
        try:
            pid = open('ingest.pid').read()
            if str(pid) != str(os.getpid()):
                print 'Other ingest process %s detected not %s, exiting' % (pid, os.getpid())
                sys.exit(2)
        except IOError:
            print 'Ingest process exiting: ingest.pid file cound not be read'
            sys.exit(3)
        except:
            traceback.print_exc()
            sys.exit(4)
        for state in ('new', 'downloaded', 'parsed'):
            for t in get_tickets(state):
                determine_action(t)
                count += 1
        time.sleep(15)
        if time.time() - last_flash > (5 * 60):
            sys.stdout.write('Ingest pipeline %s %s performed %s actions\n' % (os.getpid(), time.ctime(), count))
            last_flash = time.time()

def reset_all_tickets():
    for t in get_tickets():
        print 'Resetting', t['_id']
        t['state'] = 'new'
        t.save()

@app.route('/ticket/')
@app.route('/ticket/<ticket_id>')
def view_ticket(ticket_id=None):
    ingest_tickets = get_tickets()
    sort_key = request.values.get('sort')
    if sort_key:
        ingest_tickets.sort(key=lambda x: x.get(sort_key))
    if ticket_id:
        try:
            t = IngestTicket.load(ticket_id)
        except bibserver.ingest.IngestTicketInvalidId:
            abort(404)
    else:
        t = None
    return render_template('tickets/view.html', ticket=t, ingest_tickets = ingest_tickets)

@app.route('/ticket/<ticket_id>/<payload>', methods=['GET', 'POST'])
def ticket_serve(ticket_id, payload):
    t = IngestTicket.load(ticket_id)
    if payload == 'data':
        filename = t['data_md5']
    elif payload == 'bibjson':
        filename = t['data_json']
    elif (payload == 'reset') and (request.method == 'POST'):
        t['state'] =  'new'
        for cleanfield in ('failed_index', 'parse_feedback'):
            if cleanfield in t:
                del t[cleanfield]
        t.save()
        return make_response('OK')
    elif (payload == 'delete') and (request.method == 'POST'):
        t.delete()
        return make_response('OK')
    return redirect('/data/'+filename)

@app.route('/data.txt')
def data_list():
    'Output a list of all the raw data files, one file per line'
    data_list = []
    for t in get_tickets():
        if 'data_json' in t:
            data_list.append('/data/' + t['data_json'])
    resp = make_response( '\n'.join(data_list) )
    resp.mimetype = "text/plain"
    return resp

@app.route('/data/<filename>')
def data_serve(filename):
    path = config['download_cache_directory']
    if not path.startswith('/'):
        path = os.path.join(os.getcwd(), path)
    response = send_from_directory(path, filename)
    response.headers['Content-Type'] = 'text/plain'
    return response
    
if __name__ == '__main__':
    init()
    for x in sys.argv[1:]:        
        if x == '-x':
            reset_all_tickets()
        elif x.startswith('-p'):
            for t in get_tickets():
                print t
                if x == '-pp':
                    print '-' * 80
                    for k,v in t.items():
                        print ' '*4, k+':', v
        elif x == '-d':
            open('ingest.pid', 'w').write('%s' % os.getpid())
            run()
    if len(sys.argv) == 1:
        run()
    

########NEW FILE########
__FILENAME__ = search

from flask import Flask, request, redirect, abort, make_response
from flask import render_template, flash
import bibserver.dao
from bibserver import auth
import json, httplib
from bibserver.config import config
import bibserver.util as util


class Search(object):

    def __init__(self,path,current_user):
        self.path = path.replace(".json","")
        self.current_user = current_user

        self.search_options = {
            'search_url': '/query?',
            'search_index': 'elasticsearch',
            'paging': { 'from': 0, 'size': 10 },
            'predefined_filters': {},
            'facets': config['search_facet_fields'],
            'result_display': config['search_result_display'],
            'addremovefacets': config['add_remove_facets']      # (full list could also be pulled from DAO)
        }

        self.parts = self.path.strip('/').split('/')


    def find(self):
        if bibserver.dao.Account.get(self.parts[0]):
            if len(self.parts) == 1:
                return self.account() # user account
            elif len(self.parts) == 2:
                if self.parts[1] == "collections":
                    return self.collections()
                else:
                    return self.collection() # get a collection
            elif len(self.parts) == 3:
                return self.record() # get a record in collection
        elif self.parts[0] == 'collections':
            return self.collections() # get search list of all collections
        elif len(self.parts) == 1:
            if self.parts[0] != 'search':
                self.search_options['q'] = self.parts[0]
            return self.default() # get search result of implicit search term
        elif len(self.parts) == 2:
            return self.implicit_facet() # get search result of implicit facet filter
        else:
            abort(404)

    def default(self):
        # default search page
        if util.request_wants_json():
            res = bibserver.dao.Record.query()
            resp = make_response( json.dumps([i['_source'] for i in res['hits']['hits']], sort_keys=True, indent=4) )
            resp.mimetype = "application/json"
            return resp
        else:
            return render_template('search/index.html', 
                current_user=self.current_user, 
                search_options=json.dumps(self.search_options), 
                collection=None
            )
        

    def implicit_facet(self):
        self.search_options['predefined_filters'][self.parts[0]+config['facet_field']] = self.parts[1]
        # remove the implicit facet from facets
        for count,facet in enumerate(self.search_options['facets']):
            if facet['field'] == self.parts[0]+config['facet_field']:
                del self.search_options['facets'][count]
        if util.request_wants_json():
            res = bibserver.dao.Record.query(terms=self.search_options['predefined_filters'])
            resp = make_response( json.dumps([i['_source'] for i in res['hits']['hits']], sort_keys=True, indent=4) )
            resp.mimetype = "application/json"
            return resp
        else:
            return render_template('search/index.html', 
                current_user=self.current_user, 
                search_options=json.dumps(self.search_options), 
                collection=None, 
                implicit=self.parts[0]+': ' + self.parts[1]
            )


    def collections(self):
        if len(self.parts) == 1:
            if util.request_wants_json():
                res = bibserver.dao.Collection.query(size=1000000)
                colls = [i['_source'] for i in res['hits']['hits']]
                resp = make_response( json.dumps(colls, sort_keys=True, indent=4) )
                resp.mimetype = "application/json"
                return resp
            else:
                # search collection records
                self.search_options['search_url'] = '/query/collection?'
                self.search_options['facets'] = [{'field':'owner','size':100},{'field':'_created','size':100}]
                self.search_options['result_display'] = [[{'pre':'<h3>','field':'label','post':'</h3>'}],[{'field':'description'}],[{'pre':'created by ','field':'owner'}]]
                self.search_options['result_display'] = config['colls_result_display']
                return render_template('collection/index.html', current_user=self.current_user, search_options=json.dumps(self.search_options), collection=None)
        elif len(self.parts) == 2:
            if self.parts[0] == "collections":
                acc = bibserver.dao.Account.get(self.parts[1])
            else:
                acc = bibserver.dao.Account.get(self.parts[0])
            if acc:
                resp = make_response( json.dumps([coll.data for coll in acc.collections], sort_keys=True, indent=4) )
                resp.mimetype = "application/json"
                return resp
            else:
                abort(404)
        elif len(self.parts) == 3:
            coll = bibserver.dao.Collection.get_by_owner_coll(self.parts[1],self.parts[2])
            if coll:
                coll.data['records'] = len(coll)
                resp = make_response( json.dumps(coll.data, sort_keys=True, indent=4) )
                resp.mimetype = "application/json"
                return resp
            else:
                abort(404)
        else:
            abort(404)
            

    def record(self):
        found = None
        res = bibserver.dao.Record.query(terms = {
            'owner'+config['facet_field']:self.parts[0],
            'collection'+config['facet_field']:self.parts[1],
            'id'+config['facet_field']:self.parts[2]
        })
        if res['hits']['total'] == 0:
            rec = bibserver.dao.Record.get(self.parts[2])
            if rec: found = 1
        elif res['hits']['total'] == 1:
            rec = bibserver.dao.Record.get(res['hits']['hits'][0]['_id'])
            found = 1
        else:
            found = 2

        if not found:
            abort(404)
        elif found == 1:
            collection = bibserver.dao.Collection.get_by_owner_coll(rec.data['owner'],rec.data['collection'])
            if request.method == 'DELETE':
                if rec:
                    if not auth.collection.update(self.current_user, collection):
                        abort(401)
                    rec.delete()
                    abort(404)
                else:
                    abort(404)
            elif request.method == 'POST':
                if rec:
                    if not auth.collection.update(self.current_user, collection):
                        abort(401)
                    rec.data = request.json
                    rec.save()
                    resp = make_response( json.dumps(rec.data, sort_keys=True, indent=4) )
                    resp.mimetype = "application/json"
                    return resp
            else:
                if util.request_wants_json():
                    resp = make_response( json.dumps(rec.data, sort_keys=True, indent=4) )
                    resp.mimetype = "application/json"
                    return resp
                else:
                    admin = True if auth.collection.update(self.current_user, collection) else False
                    
                    # make a list of all the values in the record, for autocomplete on the search field
                    searchvals = []
                    def valloop(obj):
                        if isinstance(obj,dict):
                            for item in obj:
                                valloop(obj[item])
                        elif isinstance(obj,list):
                            for thing in obj:
                                valloop(thing)
                        else:
                            searchvals.append(obj)
                    valloop(rec.data)
                    
                    # get fuzzy like this
                    host = str(config['ELASTIC_SEARCH_HOST']).rstrip('/')
                    db_path = config['ELASTIC_SEARCH_DB']
                    fullpath = '/' + db_path + '/record/' + rec.id + '/_mlt?mlt_fields=title&min_term_freq=1&percent_terms_to_match=1&min_word_len=3'                    
                    c = httplib.HTTPConnection(host)
                    c.request('GET', fullpath)
                    resp = c.getresponse()
                    res = json.loads(resp.read())
                    mlt = [i['_source'] for i in res['hits']['hits']]
                    
                    # get any notes
                    notes = bibserver.dao.Note.about(rec.id)
                    
                    # check service core for more data about the record
                    # TODO: should maybe move this into the record dao or something
                    # TODO: also, add in any other calls to external APIs
                    servicecore = ""
                    apis = config['external_apis']
                    if apis['servicecore']['key']:
                        try:
                            servicecore = "not found in any UK repository"
                            addr = apis['servicecore']['url'] + rec.data['title'].replace(' ','%20') + "?format=json&api_key=" + apis['servicecore']['key']
                            import urllib2
                            response = urllib2.urlopen( addr )
                            data = json.loads(response.read())

                            if 'ListRecords' in data and len(data['ListRecords']) != 0:
                                record = data['ListRecords'][0]['record']['metadata']['oai_dc:dc']
                                servicecore = "<h3>Availability</h3><p>This article is openly available in an institutional repository:</p>"
                                servicecore += '<p><a target="_blank" href="' + record["dc:source"] + '">' + record["dc:title"] + '</a><br />'
                                if "dc:description" in record:
                                    servicecore += record["dc:description"] + '<br /><br />'
                                servicecore += '</p>'
                        except:
                            pass
                    
                    # render the record with all extras
                    return render_template('record.html', 
                        record=json.dumps(rec.data), 
                        prettyrecord=self.prettify(rec.data),
                        objectrecord = rec.data,
                        searchvals=json.dumps(searchvals),
                        admin=admin,
                        notes=notes,
                        servicecore=servicecore,
                        mlt=mlt,
                        searchables=json.dumps(config["searchables"], sort_keys=True)
                    )
        else:
            if util.request_wants_json():
                resp = make_response( json.dumps([i['_source'] for i in res['hits']['hits']], sort_keys=True, indent=4) )
                resp.mimetype = "application/json"
                return resp
            else:
                return render_template('record.html', multiple=[i['_source'] for i in res['hits']['hits']])


    def account(self):
        self.search_options['predefined_filters']['owner'+config['facet_field']] = self.parts[0]
        acc = bibserver.dao.Account.get(self.parts[0])

        if request.method == 'DELETE':
            if not auth.user.update(self.current_user,acc):
                abort(401)
            if acc: acc.delete()
            return ''
        elif request.method == 'POST':
            if not auth.user.update(self.current_user,acc):
                abort(401)
            info = request.json
            if info.get('_id',False):
                if info['_id'] != self.parts[0]:
                    acc = bibserver.dao.Account.get(info['_id'])
                else:
                    info['api_key'] = acc.data['api_key']
                    info['_created'] = acc.data['_created']
                    info['collection'] = acc.data['collection']
                    info['owner'] = acc.data['collection']
            acc.data = info
            if 'password' in info and not info['password'].startswith('sha1'):
                acc.set_password(info['password'])
            acc.save()
            resp = make_response( json.dumps(acc.data, sort_keys=True, indent=4) )
            resp.mimetype = "application/json"
            return resp
        else:
            if util.request_wants_json():
                if not auth.user.update(self.current_user,acc):
                    abort(401)
                resp = make_response( json.dumps(acc.data, sort_keys=True, indent=4) )
                resp.mimetype = "application/json"
                return resp
            else:
                admin = True if auth.user.update(self.current_user,acc) else False
                recordcount = bibserver.dao.Record.query(terms={'owner':acc.id})['hits']['total']
                collcount = bibserver.dao.Collection.query(terms={'owner':acc.id})['hits']['total']
                return render_template('account/view.html', 
                    current_user=self.current_user, 
                    search_options=json.dumps(self.search_options), 
                    record=json.dumps(acc.data), 
                    recordcount=recordcount,
                    collcount=collcount,
                    admin=admin,
                    account=acc,
                    superuser=auth.user.is_super(self.current_user)
                )


    def collection(self):
        # show the collection that matches parts[1]
        self.search_options['predefined_filters']['owner'] = self.parts[0]
        self.search_options['predefined_filters']['collection'] = self.parts[1]

        # remove the collection facet
        for count,facet in enumerate(self.search_options['facets']):
            if facet['field'] == 'collection'+config['facet_field']:
                del self.search_options['facets'][count]

        # look for collection metadata
        metadata = bibserver.dao.Collection.get_by_owner_coll(self.parts[0],self.parts[1])

        if request.method == 'DELETE':
            if metadata != None:
                if not auth.collection.update(self.current_user, metadata):
                    abort(401)
                else: metadata.delete()
                return ''
            else:
                if not auth.collection.create(self.current_user, None):
                    abort(401)
                else:
                    size = bibserver.dao.Record.query(terms={'owner':self.parts[0],'collection':self.parts[1]})['hits']['total']
                    for rid in bibserver.dao.Record.query(terms={'owner':self.parts[0],'collection':self.parts[1]},size=size)['hits']['hits']:
                        record = bibserver.dao.Record.get(rid['_id'])
                        if record: record.delete()
                    return ''
        elif request.method == 'POST':
            if metadata != None:
                metadata.data = request.json
                metadata.save()
                return ''
            else: abort(404)
        else:
            if util.request_wants_json():
                out = {"metadata":metadata.data,"records":[]}
                out['metadata']['records'] = len(metadata)
                out['metadata']['query'] = request.url
                for rec in metadata.records:
                    out['records'].append(rec.data)
                resp = make_response( json.dumps(out, sort_keys=True, indent=4) )
                resp.mimetype = "application/json"
                return resp
            else:
                admin = True if metadata != None and auth.collection.update(self.current_user, metadata) else False
                if metadata and '_display_settings' in metadata:
                    self.search_options.update(metadata['_display_settings'])
                users = bibserver.dao.Account.query(size=1000000) # pass the userlist for autocomplete admin addition (could be ajax'd)
                userlist = [i['_source']['_id'] for i in users['hits']['hits']]
                return render_template('search/index.html', 
                    current_user=self.current_user, 
                    search_options=json.dumps(self.search_options), 
                    collection=metadata.data, 
                    record = json.dumps(metadata.data),
                    userlist=json.dumps(userlist),
                    request=request,
                    admin=admin
                )


    def prettify(self,record):
        result = '<p>'
        # given a result record, build how it should look on the page
        img = False
        if img:
            result += '<img class="thumbnail" style="float:left; width:100px; margin:0 5px 10px 0; max-height:150px;" src="' + img[0] + '" />'

        # add the record based on display template if available
        display = config['search_result_display']
        lines = ''
        for lineitem in display:
            line = ''
            for obj in lineitem:
                thekey = obj['field']
                parts = thekey.split('.')
                if len(parts) == 1:
                    res = record
                elif len(parts) == 2:
                    res = record.get(parts[0],'')
                elif len(parts) == 3:
                    res = record[parts[0]][parts[1]]
                counter = len(parts) - 1
                if res and isinstance(res, dict):
                    thevalue = res.get(parts[counter],'')  # this is a dict
                else:
                    thevalue = []
                    for row in res:
                        thevalue.append(row[parts[counter]])

                if thevalue and len(thevalue):
                    line += obj.get('pre','')
                    if isinstance(thevalue, list):
                        for index,val in enumerate(thevalue):
                            if index != 0 and index != len(thevalue)-1: line += ', '
                            line += val
                    else:
                        line += thevalue
                    line += obj.get('post','')
            if line:
                lines += line + "<br />"
        if lines:
            result += lines
        else:
            result += json.dumps(record,sort_keys=True,indent=4)
        result += '</p>'
        return result




########NEW FILE########
__FILENAME__ = util
from urllib import urlopen, urlencode
import md5
import re
from unicodedata import normalize
from functools import wraps
from flask import request, current_app


def jsonp(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = str(callback) + '(' + str(f(*args,**kwargs).data) + ')'
            return current_app.response_class(content, mimetype='application/javascript')
        else:
            return f(*args, **kwargs)
    return decorated_function


# derived from http://flask.pocoo.org/snippets/45/ (pd) and customised
def request_wants_json():
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    if best == 'application/json' and request.accept_mimetypes[best] > request.accept_mimetypes['text/html']:
        best = True
    else:
        best = False
    if request.values.get('format','').lower() == 'json' or request.path.endswith(".json"):
        best = True
    return best
        

# derived from http://flask.pocoo.org/snippets/5/ (public domain)
# changed delimiter to _ instead of - due to ES search problem on the -
_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
def slugify(text, delim=u'_'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))


# get gravatar for email address
def get_gravatar(email, size=None, default=None, border=None):
    email = email.lower().strip()
    hash = md5.md5(email).hexdigest()
    args = {'gravatar_id':hash}
    if size and 1 <= int(size) <= 512:
        args['size'] = size
    if default: args['default'] = default
    if border: args['border'] = border

    url = 'http://www.gravatar.com/avatar.php?' + urlencode(args)

    response = urlopen(url)
    image = response.read()
    response.close()

    return image


########NEW FILE########
__FILENAME__ = account
import uuid

from flask import Blueprint, request, url_for, flash, redirect
from flask import render_template
from flask.ext.login import login_user, logout_user
from flask.ext.wtf import Form, TextField, TextAreaField, PasswordField, validators, ValidationError

from bibserver.config import config
import bibserver.dao as dao

blueprint = Blueprint('account', __name__)


@blueprint.route('/')
def index():
    return 'Accounts'


class LoginForm(Form):
    username = TextField('Username', [validators.Required()])
    password = PasswordField('Password', [validators.Required()])

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form, csrf_enabled=False)
    if request.method == 'POST' and form.validate():
        password = form.password.data
        username = form.username.data
        user = dao.Account.get(username)
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash('Welcome back', 'success')
            return redirect('/'+user.id)
        else:
            flash('Incorrect username/password', 'error')
    if request.method == 'POST' and not form.validate():
        flash('Invalid form', 'error')
    return render_template('account/login.html', form=form, upload=config['allow_upload'])


@blueprint.route('/logout')
def logout():
    logout_user()
    flash('You are now logged out', 'success')
    return redirect(url_for('home'))


def existscheck(form, field):
    test = dao.Account.get(form.w.data)
    if test:
        raise ValidationError('Taken! Please try another.')

class RegisterForm(Form):
    w = TextField('Username', [validators.Length(min=3, max=25),existscheck])
    n = TextField('Email Address', [validators.Length(min=3, max=35), validators.Email(message='Must be a valid email address')])
    s = PasswordField('Password', [
        validators.Required(),
        validators.EqualTo('c', message='Passwords must match')
    ])
    c = PasswordField('Repeat Password')
    d = TextAreaField('Describe yourself')

@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    # TODO: re-enable csrf
    form = RegisterForm(request.form, csrf_enabled=False)
    if request.method == 'POST' and form.validate():
        api_key = str(uuid.uuid4())
        account = dao.Account(
            _id=form.w.data, 
            email=form.n.data,
            description = form.d.data,
            api_key=api_key
        )
        account.set_password(form.s.data)
        account.save()
        login_user(account, remember=True)
        flash('Thanks for signing-up', 'success')
        return redirect('/'+account.id)
    if request.method == 'POST' and not form.validate():
        flash('Please correct the errors', 'error')
    return render_template('account/register.html', form=form)


########NEW FILE########
__FILENAME__ = web
import os
import urllib2
import unicodedata
import httplib
import json
import subprocess
from copy import deepcopy
from datetime import datetime

from flask import Flask, jsonify, json, request, redirect, abort, make_response
from flask import render_template, flash
from flask.views import View, MethodView
from flask.ext.login import login_user, current_user

import bibserver.dao
import bibserver.util as util
import bibserver.importer
import bibserver.ingest
from bibserver.config import config
from bibserver.core import app, login_manager
from bibserver.view.account import blueprint as account
from bibserver import auth


app.register_blueprint(account, url_prefix='/account')

# NB: the decorator appears to kill the function for normal usage
@login_manager.user_loader
def load_account_for_login_manager(userid):
    out = bibserver.dao.Account.get(userid)
    return out

@app.context_processor
def set_current_user():
    """ Set some template context globals. """
    return dict(current_user=current_user)

@app.before_request
def standard_authentication():
    """Check remote_user on a per-request basis."""
    remote_user = request.headers.get('REMOTE_USER', '')
    if remote_user:
        user = bibserver.dao.Account.get(remote_user)
        if user:
            login_user(user, remember=False)
    # add a check for provision of api key
    elif 'api_key' in request.values:
        res = bibserver.dao.Account.query(q='api_key:"' + request.values['api_key'] + '"')['hits']['hits']
        if len(res) == 1:
            user = bibserver.dao.Account.get(res[0]['_source']['_id'])
            if user:
                login_user(user, remember=False)


@app.route('/query/<path:path>', methods=['GET','POST'])
@app.route('/query/', methods=['GET','POST'])
@app.route('/query', methods=['GET','POST'])
def query(path='Record'):
    pathparts = path.split('/')
    subpath = pathparts[0]
    if subpath.lower() == 'account':
        abort(401)
    klass = getattr(bibserver.dao, subpath[0].capitalize() + subpath[1:] )
    qs = request.query_string
    if request.method == "POST":
        qs += "&source=" + json.dumps(dict(request.form).keys()[-1])
    if len(pathparts) > 1 and pathparts[1] == '_mapping':
        resp = make_response( json.dumps(klass().get_mapping()) )
    else:
        resp = make_response( klass().raw_query(qs) )
    resp.mimetype = "application/json"
    return resp
        
@app.route('/faq')
def content():
    return render_template('home/faq.html')


@app.route('/')
def home():
    data = []
    try:
        colldata = bibserver.dao.Collection.query(sort={"_created.exact":{"order":"desc"}},size=20)
        if colldata['hits']['total'] != 0:
            for coll in colldata['hits']['hits']:
                colln = bibserver.dao.Collection.get(coll['_id'])
                if colln:
                    data.append({
                        'name': colln['label'], 
                        'records': len(colln), 
                        'owner': colln['owner'], 
                        'slug': colln['collection'],
                        'description': colln['description']
                    })
    except:
        pass
    colls = bibserver.dao.Collection.query()['hits']['total']
    records = bibserver.dao.Record.query()['hits']['total']
    users = bibserver.dao.Account.query()['hits']['total']
    print data
    return render_template('home/index.html', colldata=json.dumps(data), colls=colls, records=records, users=users)


@app.route('/users')
@app.route('/users.json')
def users():
    if current_user.is_anonymous():
        abort(401)
    users = bibserver.dao.Account.query(sort={'_id':{'order':'asc'}},size=1000000)
    if users['hits']['total'] != 0:
        accs = [bibserver.dao.Account.get(i['_source']['_id']) for i in users['hits']['hits']]
        # explicitly mapped to ensure no leakage of sensitive data. augment as necessary
        users = []
        for acc in accs:
            user = {"collections":len(acc.collections),"_id":acc["_id"]}
            try:
                user['_created'] = acc['_created']
                user['description'] = acc['description']
            except:
                pass
            users.append(user)
    if util.request_wants_json():
        resp = make_response( json.dumps(users, sort_keys=True, indent=4) )
        resp.mimetype = "application/json"
        return resp
    else:
        return render_template('account/users.html',users=users)
    
# handle or disable uploads
class UploadView(MethodView):
    def get(self):
        if not auth.collection.create(current_user, None):
            flash('You need to login to upload a collection.')
            return redirect('/account/login')
        if request.values.get("source") is not None:
            return self.post()        
        return render_template('upload.html',
                               parser_plugins=bibserver.ingest.get_plugins().values())

    def post(self):
        if not auth.collection.create(current_user, None):
            abort(401)
        try:
            if not request.values.get('collection',None):
                flash('You need to provide a collection name.')
                return redirect('/upload')
            if not request.values.get('source',None):
                if not request.files.get('upfile',None):
                    if not request.json:
                        flash('You need to provide a source URL or an upload file.')
                        return redirect('/upload')
                
            collection = request.values.get('collection')
            format=request.values.get('format')
            if request.files.get('upfile'):
                fileobj = request.files.get('upfile')
                if not format:
                    format = bibserver.importer.findformat(fileobj.filename)
            else:
                if not format:
                    format = bibserver.importer.findformat( request.values.get("source").strip('"') )
            
            ticket = bibserver.ingest.IngestTicket(owner=current_user.id, 
                                       source_url=request.values.get("source"),
                                       format=format,
                                       collection=request.values.get('collection'),
                                       description=request.values.get('description'),
                                       )
            # Allow only parsing
            only_parse = request.values.get('only_parse')
            if only_parse:
               ticket['only_parse'] = True
            
            license = request.values.get('license')
            if license: ticket['license'] = license
            
            # If the user is uploading a file, update the ticket with the 'downloaded' file
            # And correct source
            if request.files.get('upfile'):
                data = fileobj.read()
                ticket['data_md5'] = bibserver.ingest.store_data_in_cache(data)
                ticket['source_url'] = config.get('SITE_URL','') + '/ticket/%s/data' % ticket.id
                ticket['state'] = 'downloaded'
            
            # if user is sending JSON, update the ticket with the received JSON
            if request.json:
                data = request.json
                ticket['data_md5'] = bibserver.ingest.store_data_in_cache(json.dumps(data))
                ticket['source_url'] = config.get('SITE_URL','') + '/ticket/%s/data' % ticket.id
                ticket['state'] = 'downloaded'

            ticket.save()
            
        except Exception, inst:
            msg = str(inst)
            if app.debug or app.config['TESTING']:
                raise
            flash('error: ' + msg)
            return render_template('upload.html')
        else:
            return redirect('/ticket/'+ticket.id)

# handle or disable uploads
class CreateView(MethodView):
    def get(self):
        if not auth.collection.create(current_user, None):
            flash('You need to login to create a collection.')
            return redirect('/account/login')
        if request.values.get("source") is not None:
            return self.post()        
        return render_template('create.html')

    def post(self):
        if not auth.collection.create(current_user, None):
            abort(401)

        # create the new collection for current user
        coll = {
            'label' : request.values.get('collection'),
            'license' : request.values.get('license')
        }
        i = bibserver.importer.Importer(current_user)
        collection, records = i.index(coll, {})
        return redirect(collection['owner'] + '/' + collection['collection'])

# a class for use when upload / create are disabled
class NoUploadOrCreate(MethodView):
    def get(self):
        return render_template('disabled.html')

    def post(self):
        abort(401)    

# set the upload / create views as appropriate
if config["allow_upload"]:
    app.add_url_rule('/upload', view_func=UploadView.as_view('upload'))
    app.add_url_rule('/create', view_func=CreateView.as_view('create'))
else:
    app.add_url_rule('/upload', view_func=NoUploadOrCreate.as_view('upload'))
    app.add_url_rule('/create', view_func=NoUploadOrCreate.as_view('create'))


# set the route for receiving new notes
@app.route('/note', methods=['GET','POST'])
@app.route('/note/<nid>', methods=['GET','POST','DELETE'])
def note(nid=''):
    if current_user.is_anonymous():
        abort(401)

    elif request.method == 'POST':
        newnote = bibserver.dao.Note()
        newnote.data = request.json
        newnote.save()
        return redirect('/note/' + newnote.id)

    elif request.method == 'DELETE':
        note = bibserver.dao.Note.get(nid)
        note.delete()
        return redirect('/note')

    else:
        thenote = bibserver.dao.Note.get(nid)
        if thenote:
            resp = make_response( json.dumps(thenote.data, sort_keys=True, indent=4) )
            resp.mimetype = "application/json"
            return resp
        else:
            abort(404)


# this is a catch-all that allows us to present everything as a search
# typical catches are /user, /user/collection, /user/collection/record, 
# /implicit_facet_key/implicit_facet_value
# and any thing else passed as a search
@app.route('/<path:path>', methods=['GET','POST','DELETE'])
def default(path):
    import bibserver.search
    searcher = bibserver.search.Search(path=path,current_user=current_user)
    return searcher.find()


if __name__ == "__main__":
    if config["allow_upload"]:
        bibserver.ingest.init()
        if not os.path.exists('ingest.pid'):
            ingest=subprocess.Popen(['python', 'bibserver/ingest.py'])
            open('ingest.pid', 'w').write('%s' % ingest.pid)
    try:
        bibserver.dao.init_db()
        app.run(host='0.0.0.0', debug=config['debug'], port=config['port'])
    finally:
        if os.path.exists('ingest.pid'):
            os.remove('ingest.pid')

########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python
import os
import sys
import optparse
import inspect

# does setup of cfg
from bibserver import dao


def rebuild_db():
    '''Rebuild the db'''
    conn, db = dao.get_conn()
    conn.delete_index(db)
    conn.create_index(db)

def fixtures():
    import test.base
    for dict_ in test.base.fixtures['records']:
        dao.Record.upsert(dict_)

def convert(inpath):
    '''Convert from bibtex to bibjson. One argument expected: path to bibtext
    file.
    '''
    import bibserver.parsers.BibTexParser
    import json
    parser = parsers.BibTexParser.BibTexParser()
    bibtex = open(inpath).read()
    print json.dumps(parser.parse(bibtex), indent=2, sort_keys=True)

def bulk_upload(colls_list):
    '''Take a collections list in a JSON file and use the bulk_upload importer.
    colls_list described in importer.py
    '''
    import bibserver.importer
    return bibserver.importer.bulk_upload(colls_list)
    

## ==================================================
## Misc stuff for setting up a command line interface

def _module_functions(functions):
    local_functions = dict(functions)
    for k,v in local_functions.items():
        if not inspect.isfunction(v) or k.startswith('_'):
            del local_functions[k]
    return local_functions

def _main(functions_or_object):
    isobject = inspect.isclass(functions_or_object)
    if isobject:
        _methods = _object_methods(functions_or_object)
    else:
        _methods = _module_functions(functions_or_object)

    usage = '''%prog {action}

Actions:
    '''
    usage += '\n    '.join(
        [ '%s: %s' % (name, m.__doc__.split('\n')[0] if m.__doc__ else '') for (name,m)
        in sorted(_methods.items()) ])
    parser = optparse.OptionParser(usage)
    # Optional: for a config file
    # parser.add_option('-c', '--config', dest='config',
    #         help='Config file to use.')
    options, args = parser.parse_args()

    if not args or not args[0] in _methods:
        parser.print_help()
        sys.exit(1)

    method = args[0]
    if isobject:
        getattr(functions_or_object(), method)(*args[1:])
    else:
        _methods[method](*args[1:])

__all__ = [ '_main' ]

if __name__ == '__main__':
    _main(locals())



########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# BibServer documentation build configuration file, created by
# sphinx-quickstart on Thu Jan 19 10:39:35 2012.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'BibServer'
copyright = u'2012, Open Knowledge Foundation'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

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
exclude_patterns = ['_build']

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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

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
#html_last_updated_fmt = '%b %d, %Y'

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
htmlhelp_basename = 'BibServerdoc'


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
  ('index', 'BibServer.tex', u'BibServer Documentation',
   u'Open Knowledge Foundation', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

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
    ('index', 'bibserver', u'BibServer Documentation',
     [u'Open Knowledge Foundation'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'BibServer', u'BibServer Documentation',
   u'Open Knowledge Foundation', 'BibServer', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = bibjson
#!/usr/bin/env python

'''
BibJSON identity parser.
Reads a valid BibJSON input on stdin, parses it as a JSON file.
Performs some basic validation, and outputs the serialised BibJSON on stdout.
'''

import os, sys
import json

def parse():
    data = sys.stdin.read()
    data_json = json.loads(data)
    sys.stdout.write(json.dumps(data_json, indent=2))
    
def main():
    conf = {"display_name": "BibJSON",
            "format": "jsoncheck",
            "contact": "openbiblio-dev@lists.okfn.org", 
            "bibserver_plugin": True, 
            "BibJSON_version": "0.81"}        
    for x in sys.argv[1:]:
        if x == '-bibserver':
            sys.stdout.write(json.dumps(conf))
            sys.exit()
    parse()
            
if __name__ == '__main__':
    main()    
########NEW FILE########
__FILENAME__ = bibtex
#!/usr/bin/env python

'''
BibTex parser.
'''

import sys
import string
import cStringIO
import json
import unicodedata
import re

class BibTexParser(object):

    def __init__(self, fileobj):

        data = fileobj.read()
        
        # On some sample data files, the character encoding detection simply hangs
        # We are going to default to utf8, and mandate it.
        self.encoding = 'utf8'

        # Some files have Byte-order marks inserted at the start
        if data[:3] == '\xef\xbb\xbf':
            data = data[3:]
        self.fileobj = cStringIO.StringIO(data)
        
        # set which bibjson schema this parser parses to
        self.has_metadata = False
        self.persons = []
        # if bibtex file has substition strings, they are stored here, 
        # then the values are checked for those substitions in add_val
        self.replace_dict = {}
        # pre-defined set of key changes
        self.alt_dict = {
            'keyw':'keyword',
            'keywords':'keyword',
            'authors':'author',
            'editors':'editor',
            'url':'link',
            'urls':'link',
            'links':'link',
            'subjects':'subject'
        }
        self.identifier_types = ["doi","isbn","issn"]

    def parse(self):
        '''given a fileobject, parse it for bibtex records,
        and pass them to the record parser'''
        records = []
        record = ""
        # read each line, bundle them up until they form an object, then send for parsing
        for line in self.fileobj:
            if '--BREAK--' in line:
                break
            else:
                if line.strip().startswith('@'):
                    if record != "":
                        parsed = self.parse_record(record)
                        if parsed:
                            records.append(parsed)
                    record = ""
                if len(line.strip()) > 0:
                    record += line

        # catch any remaining record and send it for parsing
        if record != "":
            parsed = self.parse_record(record)
            if parsed:
                records.append(parsed)
        return records, {}

    def parse_record(self, record):
        '''given a bibtex record, tidy whitespace and other rubbish; 
        then parse out the bibtype and citekey, then find all the
        key-value pairs it contains'''
        
        d = {}
        
        if not record.startswith('@'):
            return d

        # prepare record
        record = '\n'.join([i.strip() for i in record.split('\n')])
        if '}\n' in record:
            record, rubbish = record.replace('\r\n','\n').replace('\r','\n').rsplit('}\n',1)

        # if a string record, put it in the replace_dict
        if record.lower().startswith('@string'):
            key, val = [i.strip().strip('"').strip('{').strip('}').replace('\n',' ') for i in record.split('{',1)[1].strip('\n').strip(',').strip('}').split('=')]
            self.replace_dict[key] = val
            return d

        # for each line in record
        kvs = [i.strip() for i in record.split(',\n')]
        inkey = ""
        inval = ""
        for kv in kvs:
            if kv.startswith('@') and not inkey:
                # it is the start of the record - set the bibtype and citekey (id)
                bibtype, id = kv.split('{',1)
                bibtype = self.add_key(bibtype)
                id = id.strip('}').strip(',')
            elif '=' in kv and not inkey:
                # it is a line with a key value pair on it
                key, val = [i.strip() for i in kv.split('=',1)]
                key = self.add_key(key)
                # if it looks like the value spans lines, store details for next loop
                if ( val.startswith('{') and not val.endswith('}') ) or ( val.startswith('"') and not val.replace('}','').endswith('"') ):
                    inkey = key
                    inval = val
                else:
                    d[key] = self.add_val(val)
            elif inkey:
                # if this line continues the value from a previous line, append
                inval += kv
                # if it looks like this line finishes the value, store it and clear for next loop
                if ( inval.startswith('{') and inval.endswith('}') ) or ( inval.startswith('"') and inval.endswith('"') ):
                    d[inkey] = self.add_val(inval)
                    inkey = ""
                    inval = ""

        # put author names into persons list
        if 'author_data' in d:
            self.persons = [i for i in d['author_data'].split('\n')]
            del d['author_data']

        if not d:
            return d

        d['type'] = bibtype
        d['id'] = id
        if not self.has_metadata and 'type' in d:
            if d['type'] == 'personal bibliography' or d['type'] == 'comment':
                self.has_metadata = True

        # apply any customisations to the record object then return it
        return self.customisations(d)

    def customisations(self,record):
        '''alters some values to fit bibjson format'''
        if 'eprint' in record and not 'year' in record: 
            yy = '????'
            ss = record['eprint'].split('/')
            if len(ss) == 2: yy = ss[1][0:2]
            if yy[0] in ['0']: record['year'] = '20' + yy
            elif yy[0] in ['9']: record['year'] = '19' + yy
        if "pages" in record:
            if "-" in record["pages"]:
                p = [i.strip().strip('-') for i in record["pages"].split("-")]
                record["pages"] = p[0] + ' to ' + p[-1]
        if "type" in record:
            record["type"] = record["type"].lower()
        if "author" in record:
            if record["author"]:
                record["author"] = self.getnames([i.strip() for i in record["author"].replace('\n',' ').split(" and ")])
                # convert author to object
                record["author"] = [{"name":i,"id":i.replace(',','').replace(' ','').replace('.','')} for i in record["author"]]
            else:
                del record["author"]
        if "editor" in record:
            if record["editor"]:
                record["editor"] = self.getnames([i.strip() for i in record["editor"].replace('\n',' ').split(" and ")])
                # convert editor to object
                record["editor"] = [{"name":i,"id":i.replace(',','').replace(' ','').replace('.','')} for i in record["editor"]]
            else:
                del record["editor"]
        if "journal" in record:
            # switch journal to object
            if record["journal"]:
                record["journal"] = {"name":record["journal"],"id":record["journal"].replace(',','').replace(' ','').replace('.','')}
        if "keyword" in record:
            record["keyword"] = [i.strip() for i in record["keyword"].replace('\n','').split(",")]
        if "subject" in record:
            if record["subject"]:
                record["subject"] = {"name":record["subject"],"id":record["subject"].replace(',','').replace(' ','').replace('.','')}
        if "link" in record:
            links = [i.strip().replace("  "," ") for i in record["link"].split('\n')]
            record['link'] = []
            for link in links:
                parts = link.split(" ")
                linkobj = { "url":parts[0] }
                if len(parts) > 1:
                    linkobj["anchor"] = parts[1]
                if len(parts) > 2:
                    linkobj["format"] = parts[2]
                if len(linkobj["url"]) > 0:
                    record["link"].append(linkobj)
        if 'doi' in record:
            if 'link' not in record:
                record['link'] = []
            nodoi = True
            for item in record['link']:
                if 'doi' in item:
                    nodoi = False
            if nodoi:
                link = record['doi']
                if link.startswith('10'):
                    link = 'http://dx.doi.org/' + link
                record['link'].append( {"url": link, "anchor":"doi"} )
        for ident in self.identifier_types:
            if ident in record:
                if ident == 'issn':
                    if 'journal' in record:
                        if 'identifier' not in record['journal']:
                            record['journal']['identifier'] = []
                        record['journal']['identifier'].append({"id":record[ident], "type":"issn"})
                else:
                    if 'identifier' not in record:
                        record['identifier'] = []
                    record['identifier'].append({"id":record[ident], "type":ident})
                del record[ident]
        
        return record


    # some methods to tidy and format keys and vals

    def strip_quotes(self, val):
        """Strip double quotes enclosing string"""
        val = val.strip()
        if val.startswith('"') and val.endswith('"'):
            return val[1:-1]
        return val

    def strip_braces(self, val):
        """Strip braces enclosing string"""
        val.strip()
        if val.startswith('{') and val.endswith('}'):
            return val[1:-1]
        return val

    def string_subst(self, val):
        """ Substitute string definitions """
        if not val:
            return u''
        for k in self.replace_dict.keys():
            if val == k:
                val = self.replace_dict[k]
        if not isinstance(val, unicode):
            val = unicode(val,self.encoding,'ignore')
        if '\\' in val or '{' in val:
            for k, v in self.unicode_to_latex.iteritems():
                if v in val:
                    parts = val.split(str(v))
                    for key,val in enumerate(parts):
                        if key+1 < len(parts) and len(parts[key+1]) > 0:
                            parts[key+1] = parts[key+1][0:]
                    val = k.join(parts)
                val = val.replace("{","").replace("}","")
        return val

    def add_val(self, val):
        if not val or val == "{}":
            return u''
        """ Clean instring before adding to dictionary """
        val = self.strip_braces(val)
        val = self.strip_quotes(val)
        val = self.strip_braces(val)
        val = self.string_subst(val)
        """alter based on particular key types"""
        return unicodedata.normalize('NFKD', val).replace(u'\x00', '').replace(u'\x1A', '')


    def add_key(self, key):
        key = key.strip().strip('@').lower()
        if key in self.alt_dict.keys():
            key = self.alt_dict[key]
        if not isinstance(key, unicode):
            return unicode(key,'utf-8')
        else:
            return key


    ''' make people names as surname, firstnames
    or surname, initials. should eventually combine up the two'''
    def getnames(self,names):
        tidynames = []
        for namestring in names:
            namestring = namestring.strip()
            if len(namestring) < 1: continue
            if ',' in namestring:
                namesplit = namestring.split(',',1)
                last = namesplit[0].strip()
                firsts = [i.strip().strip('.') for i in namesplit[1].split()]
            else:
                namesplit = namestring.split()
                last = namesplit.pop()
                firsts = [i.replace('.',' ').strip() for i in namesplit]
            if last in ['jnr','jr','junior']:
                last = firsts.pop()
            for item in firsts:
                if item in ['van','der','de','la']:
                    last = firsts.pop() + ' ' + last
            tidynames.append(last + ", " + ' '.join(firsts))
        return tidynames


    # list of latex conversions from
    # https://gist.github.com/798549
    unicode_to_latex = {
        u"\u0020": "\\space ",
        u"\u0023": "\\#",
        u"\u0024": "\\textdollar ",
        u"\u0025": "\\%",
        u"\u0026": "\\&amp;",
        u"\u0027": "\\textquotesingle ",
        u"\u002A": "\\ast ",
        u"\u005C": "\\textbackslash ",
        u"\u005E": "\\^{}",
        u"\u005F": "\\_",
        u"\u0060": "\\textasciigrave ",
        u"\u007B": "\\lbrace ",
        u"\u007C": "\\vert ",
        u"\u007D": "\\rbrace ",
        u"\u007E": "\\textasciitilde ",
        u"\u00A1": "\\textexclamdown ",
        u"\u00A2": "\\textcent ",
        u"\u00A3": "\\textsterling ",
        u"\u00A4": "\\textcurrency ",
        u"\u00A5": "\\textyen ",
        u"\u00A6": "\\textbrokenbar ",
        u"\u00A7": "\\textsection ",
        u"\u00A8": "\\textasciidieresis ",
        u"\u00A9": "\\textcopyright ",
        u"\u00AA": "\\textordfeminine ",
        u"\u00AB": "\\guillemotleft ",
        u"\u00AC": "\\lnot ",
        u"\u00AD": "\\-",
        u"\u00AE": "\\textregistered ",
        u"\u00AF": "\\textasciimacron ",
        u"\u00B0": "\\textdegree ",
        u"\u00B1": "\\pm ",
        u"\u00B2": "{^2}",
        u"\u00B3": "{^3}",
        u"\u00B4": "\\textasciiacute ",
        u"\u00B5": "\\mathrm{\\mu}",
        u"\u00B6": "\\textparagraph ",
        u"\u00B7": "\\cdot ",
        u"\u00B8": "\\c{}",
        u"\u00B9": "{^1}",
        u"\u00BA": "\\textordmasculine ",
        u"\u00BB": "\\guillemotright ",
        u"\u00BC": "\\textonequarter ",
        u"\u00BD": "\\textonehalf ",
        u"\u00BE": "\\textthreequarters ",
        u"\u00BF": "\\textquestiondown ",
        u"\u00C0": "\\`{A}",
        u"\u00C1": "\\'{A}",
        u"\u00C2": "\\^{A}",
        u"\u00C3": "\\~{A}",
        u"\u00C4": "\\\"{A}",
        u"\u00C5": "\\AA ",
        u"\u00C6": "\\AE ",
        u"\u00C7": "\\c{C}",
        u"\u00C8": "\\`{E}",
        u"\u00C9": "\\'{E}",
        u"\u00CA": "\\^{E}",
        u"\u00CB": "\\\"{E}",
        u"\u00CC": "\\`{I}",
        u"\u00CD": "\\'{I}",
        u"\u00CE": "\\^{I}",
        u"\u00CF": "\\\"{I}",
        u"\u00D0": "\\DH ",
        u"\u00D1": "\\~{N}",
        u"\u00D2": "\\`{O}",
        u"\u00D3": "\\'{O}",
        u"\u00D4": "\\^{O}",
        u"\u00D5": "\\~{O}",
        u"\u00D6": "\\\"{O}",
        u"\u00D7": "\\texttimes ",
        u"\u00D8": "\\O ",
        u"\u00D9": "\\`{U}",
        u"\u00DA": "\\'{U}",
        u"\u00DB": "\\^{U}",
        u"\u00DC": "\\\"{U}",
        u"\u00DD": "\\'{Y}",
        u"\u00DE": "\\TH ",
        u"\u00DF": "\\ss ",
        u"\u00E0": "\\`{a}",
        u"\u00E1": "\\'{a}",
        u"\u00E2": "\\^{a}",
        u"\u00E3": "\\~{a}",
        u"\u00E4": "\\\"{a}",
        u"\u00E5": "\\aa ",
        u"\u00E6": "\\ae ",
        u"\u00E7": "\\c{c}",
        u"\u00E8": "\\`{e}",
        u"\u00E9": "\\'{e}",
        u"\u00EA": "\\^{e}",
        u"\u00EB": "\\\"{e}",
        u"\u00EC": "\\`{\\i}",
        u"\u00ED": "\\'{\\i}",
        u"\u00EE": "\\^{\\i}",
        u"\u00EF": "\\\"{\\i}",
        u"\u00F0": "\\dh ",
        u"\u00F1": "\\~{n}",
        u"\u00F2": "\\`{o}",
        u"\u00F3": "\\'{o}",
        u"\u00F4": "\\^{o}",
        u"\u00F5": "\\~{o}",
        u"\u00F6": "\\\"{o}",
        u"\u00F7": "\\div ",
        u"\u00F8": "\\o ",
        u"\u00F9": "\\`{u}",
        u"\u00FA": "\\'{u}",
        u"\u00FB": "\\^{u}",
        u"\u00FC": "\\\"{u}",
        u"\u00FD": "\\'{y}",
        u"\u00FE": "\\th ",
        u"\u00FF": "\\\"{y}",
        u"\u0100": "\\={A}",
        u"\u0101": "\\={a}",
        u"\u0102": "\\u{A}",
        u"\u0103": "\\u{a}",
        u"\u0104": "\\k{A}",
        u"\u0105": "\\k{a}",
        u"\u0106": "\\'{C}",
        u"\u0107": "\\'{c}",
        u"\u0108": "\\^{C}",
        u"\u0109": "\\^{c}",
        u"\u010A": "\\.{C}",
        u"\u010B": "\\.{c}",
        u"\u010C": "\\v{C}",
        u"\u010D": "\\v{c}",
        u"\u010E": "\\v{D}",
        u"\u010F": "\\v{d}",
        u"\u0110": "\\DJ ",
        u"\u0111": "\\dj ",
        u"\u0112": "\\={E}",
        u"\u0113": "\\={e}",
        u"\u0114": "\\u{E}",
        u"\u0115": "\\u{e}",
        u"\u0116": "\\.{E}",
        u"\u0117": "\\.{e}",
        u"\u0118": "\\k{E}",
        u"\u0119": "\\k{e}",
        u"\u011A": "\\v{E}",
        u"\u011B": "\\v{e}",
        u"\u011C": "\\^{G}",
        u"\u011D": "\\^{g}",
        u"\u011E": "\\u{G}",
        u"\u011F": "\\u{g}",
        u"\u0120": "\\.{G}",
        u"\u0121": "\\.{g}",
        u"\u0122": "\\c{G}",
        u"\u0123": "\\c{g}",
        u"\u0124": "\\^{H}",
        u"\u0125": "\\^{h}",
        u"\u0126": "{\\fontencoding{LELA}\\selectfont\\char40}",
        u"\u0127": "\\Elzxh ",
        u"\u0128": "\\~{I}",
        u"\u0129": "\\~{\\i}",
        u"\u012A": "\\={I}",
        u"\u012B": "\\={\\i}",
        u"\u012C": "\\u{I}",
        u"\u012D": "\\u{\\i}",
        u"\u012E": "\\k{I}",
        u"\u012F": "\\k{i}",
        u"\u0130": "\\.{I}",
        u"\u0131": "\\i ",
#        u"\u0132": "IJ",
#        u"\u0133": "ij",
        u"\u0134": "\\^{J}",
        u"\u0135": "\\^{\\j}",
        u"\u0136": "\\c{K}",
        u"\u0137": "\\c{k}",
        u"\u0138": "{\\fontencoding{LELA}\\selectfont\\char91}",
        u"\u0139": "\\'{L}",
        u"\u013A": "\\'{l}",
        u"\u013B": "\\c{L}",
        u"\u013C": "\\c{l}",
        u"\u013D": "\\v{L}",
        u"\u013E": "\\v{l}",
        u"\u013F": "{\\fontencoding{LELA}\\selectfont\\char201}",
        u"\u0140": "{\\fontencoding{LELA}\\selectfont\\char202}",
        u"\u0141": "\\L ",
        u"\u0142": "\\l ",
        u"\u0143": "\\'{N}",
        u"\u0144": "\\'{n}",
        u"\u0145": "\\c{N}",
        u"\u0146": "\\c{n}",
        u"\u0147": "\\v{N}",
        u"\u0148": "\\v{n}",
        u"\u0149": "'n",
        u"\u014A": "\\NG ",
        u"\u014B": "\\ng ",
        u"\u014C": "\\={O}",
        u"\u014D": "\\={o}",
        u"\u014E": "\\u{O}",
        u"\u014F": "\\u{o}",
        u"\u0150": "\\H{O}",
        u"\u0151": "\\H{o}",
        u"\u0152": "\\OE ",
        u"\u0153": "\\oe ",
        u"\u0154": "\\'{R}",
        u"\u0155": "\\'{r}",
        u"\u0156": "\\c{R}",
        u"\u0157": "\\c{r}",
        u"\u0158": "\\v{R}",
        u"\u0159": "\\v{r}",
        u"\u015A": "\\'{S}",
        u"\u015B": "\\'{s}",
        u"\u015C": "\\^{S}",
        u"\u015D": "\\^{s}",
        u"\u015E": "\\c{S}",
        u"\u015F": "\\c{s}",
        u"\u0160": "\\v{S}",
        u"\u0161": "\\v{s}",
        u"\u0162": "\\c{T}",
        u"\u0163": "\\c{t}",
        u"\u0164": "\\v{T}",
        u"\u0165": "\\v{t}",
        u"\u0166": "{\\fontencoding{LELA}\\selectfont\\char47}",
        u"\u0167": "{\\fontencoding{LELA}\\selectfont\\char63}",
        u"\u0168": "\\~{U}",
        u"\u0169": "\\~{u}",
        u"\u016A": "\\={U}",
        u"\u016B": "\\={u}",
        u"\u016C": "\\u{U}",
        u"\u016D": "\\u{u}",
        u"\u016E": "\\r{U}",
        u"\u016F": "\\r{u}",
        u"\u0170": "\\H{U}",
        u"\u0171": "\\H{u}",
        u"\u0172": "\\k{U}",
        u"\u0173": "\\k{u}",
        u"\u0174": "\\^{W}",
        u"\u0175": "\\^{w}",
        u"\u0176": "\\^{Y}",
        u"\u0177": "\\^{y}",
        u"\u0178": "\\\"{Y}",
        u"\u0179": "\\'{Z}",
        u"\u017A": "\\'{z}",
        u"\u017B": "\\.{Z}",
        u"\u017C": "\\.{z}",
        u"\u017D": "\\v{Z}",
        u"\u017E": "\\v{z}",
        u"\u0195": "\\texthvlig ",
        u"\u019E": "\\textnrleg ",
        u"\u01AA": "\\eth ",
        u"\u01BA": "{\\fontencoding{LELA}\\selectfont\\char195}",
        u"\u01C2": "\\textdoublepipe ",
        u"\u01F5": "\\'{g}",
        u"\u0250": "\\Elztrna ",
        u"\u0252": "\\Elztrnsa ",
        u"\u0254": "\\Elzopeno ",
        u"\u0256": "\\Elzrtld ",
        u"\u0258": "{\\fontencoding{LEIP}\\selectfont\\char61}",
        u"\u0259": "\\Elzschwa ",
        u"\u025B": "\\varepsilon ",
        u"\u0263": "\\Elzpgamma ",
        u"\u0264": "\\Elzpbgam ",
        u"\u0265": "\\Elztrnh ",
        u"\u026C": "\\Elzbtdl ",
        u"\u026D": "\\Elzrtll ",
        u"\u026F": "\\Elztrnm ",
        u"\u0270": "\\Elztrnmlr ",
        u"\u0271": "\\Elzltlmr ",
        u"\u0272": "\\Elzltln ",
        u"\u0273": "\\Elzrtln ",
        u"\u0277": "\\Elzclomeg ",
        u"\u0278": "\\textphi ",
        u"\u0279": "\\Elztrnr ",
        u"\u027A": "\\Elztrnrl ",
        u"\u027B": "\\Elzrttrnr ",
        u"\u027C": "\\Elzrl ",
        u"\u027D": "\\Elzrtlr ",
        u"\u027E": "\\Elzfhr ",
        u"\u027F": "{\\fontencoding{LEIP}\\selectfont\\char202}",
        u"\u0282": "\\Elzrtls ",
        u"\u0283": "\\Elzesh ",
        u"\u0287": "\\Elztrnt ",
        u"\u0288": "\\Elzrtlt ",
        u"\u028A": "\\Elzpupsil ",
        u"\u028B": "\\Elzpscrv ",
        u"\u028C": "\\Elzinvv ",
        u"\u028D": "\\Elzinvw ",
        u"\u028E": "\\Elztrny ",
        u"\u0290": "\\Elzrtlz ",
        u"\u0292": "\\Elzyogh ",
        u"\u0294": "\\Elzglst ",
        u"\u0295": "\\Elzreglst ",
        u"\u0296": "\\Elzinglst ",
        u"\u029E": "\\textturnk ",
        u"\u02A4": "\\Elzdyogh ",
        u"\u02A7": "\\Elztesh ",
        u"\u02C7": "\\textasciicaron ",
        u"\u02C8": "\\Elzverts ",
        u"\u02CC": "\\Elzverti ",
        u"\u02D0": "\\Elzlmrk ",
        u"\u02D1": "\\Elzhlmrk ",
        u"\u02D2": "\\Elzsbrhr ",
        u"\u02D3": "\\Elzsblhr ",
        u"\u02D4": "\\Elzrais ",
        u"\u02D5": "\\Elzlow ",
        u"\u02D8": "\\textasciibreve ",
        u"\u02D9": "\\textperiodcentered ",
        u"\u02DA": "\\r{}",
        u"\u02DB": "\\k{}",
        u"\u02DC": "\\texttildelow ",
        u"\u02DD": "\\H{}",
        u"\u02E5": "\\tone{55}",
        u"\u02E6": "\\tone{44}",
        u"\u02E7": "\\tone{33}",
        u"\u02E8": "\\tone{22}",
        u"\u02E9": "\\tone{11}",
        u"\u0300": "\\`",
        u"\u0301": "\\'",
        u"\u0302": "\\^",
        u"\u0303": "\\~",
        u"\u0304": "\\=",
        u"\u0306": "\\u",
        u"\u0307": "\\.",
        u"\u0308": "\\\"",
        u"\u030A": "\\r",
        u"\u030B": "\\H",
        u"\u030C": "\\v",
        u"\u030F": "\\cyrchar\\C",
        u"\u0311": "{\\fontencoding{LECO}\\selectfont\\char177}",
        u"\u0318": "{\\fontencoding{LECO}\\selectfont\\char184}",
        u"\u0319": "{\\fontencoding{LECO}\\selectfont\\char185}",
        u"\u0321": "\\Elzpalh ",
        u"\u0322": "\\Elzrh ",
        u"\u0327": "\\c",
        u"\u0328": "\\k",
        u"\u032A": "\\Elzsbbrg ",
        u"\u032B": "{\\fontencoding{LECO}\\selectfont\\char203}",
        u"\u032F": "{\\fontencoding{LECO}\\selectfont\\char207}",
        u"\u0335": "\\Elzxl ",
        u"\u0336": "\\Elzbar ",
        u"\u0337": "{\\fontencoding{LECO}\\selectfont\\char215}",
        u"\u0338": "{\\fontencoding{LECO}\\selectfont\\char216}",
        u"\u033A": "{\\fontencoding{LECO}\\selectfont\\char218}",
        u"\u033B": "{\\fontencoding{LECO}\\selectfont\\char219}",
        u"\u033C": "{\\fontencoding{LECO}\\selectfont\\char220}",
        u"\u033D": "{\\fontencoding{LECO}\\selectfont\\char221}",
        u"\u0361": "{\\fontencoding{LECO}\\selectfont\\char225}",
        u"\u0386": "\\'{A}",
        u"\u0388": "\\'{E}",
        u"\u0389": "\\'{H}",
        u"\u038A": "\\'{}{I}",
        u"\u038C": "\\'{}O",
        u"\u038E": "\\mathrm{'Y}",
        u"\u038F": "\\mathrm{'\\Omega}",
        u"\u0390": "\\acute{\\ddot{\\iota}}",
        u"\u0391": "\\Alpha ",
        u"\u0392": "\\Beta ",
        u"\u0393": "\\Gamma ",
        u"\u0394": "\\Delta ",
        u"\u0395": "\\Epsilon ",
        u"\u0396": "\\Zeta ",
        u"\u0397": "\\Eta ",
        u"\u0398": "\\Theta ",
        u"\u0399": "\\Iota ",
        u"\u039A": "\\Kappa ",
        u"\u039B": "\\Lambda ",
        u"\u039E": "\\Xi ",
        u"\u03A0": "\\Pi ",
        u"\u03A1": "\\Rho ",
        u"\u03A3": "\\Sigma ",
        u"\u03A4": "\\Tau ",
        u"\u03A5": "\\Upsilon ",
        u"\u03A6": "\\Phi ",
        u"\u03A7": "\\Chi ",
        u"\u03A8": "\\Psi ",
        u"\u03A9": "\\Omega ",
        u"\u03AA": "\\mathrm{\\ddot{I}}",
        u"\u03AB": "\\mathrm{\\ddot{Y}}",
        u"\u03AC": "\\'{$\\alpha$}",
        u"\u03AD": "\\acute{\\epsilon}",
        u"\u03AE": "\\acute{\\eta}",
        u"\u03AF": "\\acute{\\iota}",
        u"\u03B0": "\\acute{\\ddot{\\upsilon}}",
        u"\u03B1": "\\alpha ",
        u"\u03B2": "\\beta ",
        u"\u03B3": "\\gamma ",
        u"\u03B4": "\\delta ",
        u"\u03B5": "\\epsilon ",
        u"\u03B6": "\\zeta ",
        u"\u03B7": "\\eta ",
        u"\u03B8": "\\texttheta ",
        u"\u03B9": "\\iota ",
        u"\u03BA": "\\kappa ",
        u"\u03BB": "\\lambda ",
        u"\u03BC": "\\mu ",
        u"\u03BD": "\\nu ",
        u"\u03BE": "\\xi ",
        u"\u03C0": "\\pi ",
        u"\u03C1": "\\rho ",
        u"\u03C2": "\\varsigma ",
        u"\u03C3": "\\sigma ",
        u"\u03C4": "\\tau ",
        u"\u03C5": "\\upsilon ",
        u"\u03C6": "\\varphi ",
        u"\u03C7": "\\chi ",
        u"\u03C8": "\\psi ",
        u"\u03C9": "\\omega ",
        u"\u03CA": "\\ddot{\\iota}",
        u"\u03CB": "\\ddot{\\upsilon}",
        u"\u03CC": "\\'{o}",
        u"\u03CD": "\\acute{\\upsilon}",
        u"\u03CE": "\\acute{\\omega}",
        u"\u03D0": "\\Pisymbol{ppi022}{87}",
        u"\u03D1": "\\textvartheta ",
        u"\u03D2": "\\Upsilon ",
        u"\u03D5": "\\phi ",
        u"\u03D6": "\\varpi ",
        u"\u03DA": "\\Stigma ",
        u"\u03DC": "\\Digamma ",
        u"\u03DD": "\\digamma ",
        u"\u03DE": "\\Koppa ",
        u"\u03E0": "\\Sampi ",
        u"\u03F0": "\\varkappa ",
        u"\u03F1": "\\varrho ",
        u"\u03F4": "\\textTheta ",
        u"\u03F6": "\\backepsilon ",
        u"\u0401": "\\cyrchar\\CYRYO ",
        u"\u0402": "\\cyrchar\\CYRDJE ",
        u"\u0403": "\\cyrchar{\\'\\CYRG}",
        u"\u0404": "\\cyrchar\\CYRIE ",
        u"\u0405": "\\cyrchar\\CYRDZE ",
        u"\u0406": "\\cyrchar\\CYRII ",
        u"\u0407": "\\cyrchar\\CYRYI ",
        u"\u0408": "\\cyrchar\\CYRJE ",
        u"\u0409": "\\cyrchar\\CYRLJE ",
        u"\u040A": "\\cyrchar\\CYRNJE ",
        u"\u040B": "\\cyrchar\\CYRTSHE ",
        u"\u040C": "\\cyrchar{\\'\\CYRK}",
        u"\u040E": "\\cyrchar\\CYRUSHRT ",
        u"\u040F": "\\cyrchar\\CYRDZHE ",
        u"\u0410": "\\cyrchar\\CYRA ",
        u"\u0411": "\\cyrchar\\CYRB ",
        u"\u0412": "\\cyrchar\\CYRV ",
        u"\u0413": "\\cyrchar\\CYRG ",
        u"\u0414": "\\cyrchar\\CYRD ",
        u"\u0415": "\\cyrchar\\CYRE ",
        u"\u0416": "\\cyrchar\\CYRZH ",
        u"\u0417": "\\cyrchar\\CYRZ ",
        u"\u0418": "\\cyrchar\\CYRI ",
        u"\u0419": "\\cyrchar\\CYRISHRT ",
        u"\u041A": "\\cyrchar\\CYRK ",
        u"\u041B": "\\cyrchar\\CYRL ",
        u"\u041C": "\\cyrchar\\CYRM ",
        u"\u041D": "\\cyrchar\\CYRN ",
        u"\u041E": "\\cyrchar\\CYRO ",
        u"\u041F": "\\cyrchar\\CYRP ",
        u"\u0420": "\\cyrchar\\CYRR ",
        u"\u0421": "\\cyrchar\\CYRS ",
        u"\u0422": "\\cyrchar\\CYRT ",
        u"\u0423": "\\cyrchar\\CYRU ",
        u"\u0424": "\\cyrchar\\CYRF ",
        u"\u0425": "\\cyrchar\\CYRH ",
        u"\u0426": "\\cyrchar\\CYRC ",
        u"\u0427": "\\cyrchar\\CYRCH ",
        u"\u0428": "\\cyrchar\\CYRSH ",
        u"\u0429": "\\cyrchar\\CYRSHCH ",
        u"\u042A": "\\cyrchar\\CYRHRDSN ",
        u"\u042B": "\\cyrchar\\CYRERY ",
        u"\u042C": "\\cyrchar\\CYRSFTSN ",
        u"\u042D": "\\cyrchar\\CYREREV ",
        u"\u042E": "\\cyrchar\\CYRYU ",
        u"\u042F": "\\cyrchar\\CYRYA ",
        u"\u0430": "\\cyrchar\\cyra ",
        u"\u0431": "\\cyrchar\\cyrb ",
        u"\u0432": "\\cyrchar\\cyrv ",
        u"\u0433": "\\cyrchar\\cyrg ",
        u"\u0434": "\\cyrchar\\cyrd ",
        u"\u0435": "\\cyrchar\\cyre ",
        u"\u0436": "\\cyrchar\\cyrzh ",
        u"\u0437": "\\cyrchar\\cyrz ",
        u"\u0438": "\\cyrchar\\cyri ",
        u"\u0439": "\\cyrchar\\cyrishrt ",
        u"\u043A": "\\cyrchar\\cyrk ",
        u"\u043B": "\\cyrchar\\cyrl ",
        u"\u043C": "\\cyrchar\\cyrm ",
        u"\u043D": "\\cyrchar\\cyrn ",
        u"\u043E": "\\cyrchar\\cyro ",
        u"\u043F": "\\cyrchar\\cyrp ",
        u"\u0440": "\\cyrchar\\cyrr ",
        u"\u0441": "\\cyrchar\\cyrs ",
        u"\u0442": "\\cyrchar\\cyrt ",
        u"\u0443": "\\cyrchar\\cyru ",
        u"\u0444": "\\cyrchar\\cyrf ",
        u"\u0445": "\\cyrchar\\cyrh ",
        u"\u0446": "\\cyrchar\\cyrc ",
        u"\u0447": "\\cyrchar\\cyrch ",
        u"\u0448": "\\cyrchar\\cyrsh ",
        u"\u0449": "\\cyrchar\\cyrshch ",
        u"\u044A": "\\cyrchar\\cyrhrdsn ",
        u"\u044B": "\\cyrchar\\cyrery ",
        u"\u044C": "\\cyrchar\\cyrsftsn ",
        u"\u044D": "\\cyrchar\\cyrerev ",
        u"\u044E": "\\cyrchar\\cyryu ",
        u"\u044F": "\\cyrchar\\cyrya ",
        u"\u0451": "\\cyrchar\\cyryo ",
        u"\u0452": "\\cyrchar\\cyrdje ",
        u"\u0453": "\\cyrchar{\\'\\cyrg}",
        u"\u0454": "\\cyrchar\\cyrie ",
        u"\u0455": "\\cyrchar\\cyrdze ",
        u"\u0456": "\\cyrchar\\cyrii ",
        u"\u0457": "\\cyrchar\\cyryi ",
        u"\u0458": "\\cyrchar\\cyrje ",
        u"\u0459": "\\cyrchar\\cyrlje ",
        u"\u045A": "\\cyrchar\\cyrnje ",
        u"\u045B": "\\cyrchar\\cyrtshe ",
        u"\u045C": "\\cyrchar{\\'\\cyrk}",
        u"\u045E": "\\cyrchar\\cyrushrt ",
        u"\u045F": "\\cyrchar\\cyrdzhe ",
        u"\u0460": "\\cyrchar\\CYROMEGA ",
        u"\u0461": "\\cyrchar\\cyromega ",
        u"\u0462": "\\cyrchar\\CYRYAT ",
        u"\u0464": "\\cyrchar\\CYRIOTE ",
        u"\u0465": "\\cyrchar\\cyriote ",
        u"\u0466": "\\cyrchar\\CYRLYUS ",
        u"\u0467": "\\cyrchar\\cyrlyus ",
        u"\u0468": "\\cyrchar\\CYRIOTLYUS ",
        u"\u0469": "\\cyrchar\\cyriotlyus ",
        u"\u046A": "\\cyrchar\\CYRBYUS ",
        u"\u046C": "\\cyrchar\\CYRIOTBYUS ",
        u"\u046D": "\\cyrchar\\cyriotbyus ",
        u"\u046E": "\\cyrchar\\CYRKSI ",
        u"\u046F": "\\cyrchar\\cyrksi ",
        u"\u0470": "\\cyrchar\\CYRPSI ",
        u"\u0471": "\\cyrchar\\cyrpsi ",
        u"\u0472": "\\cyrchar\\CYRFITA ",
        u"\u0474": "\\cyrchar\\CYRIZH ",
        u"\u0478": "\\cyrchar\\CYRUK ",
        u"\u0479": "\\cyrchar\\cyruk ",
        u"\u047A": "\\cyrchar\\CYROMEGARND ",
        u"\u047B": "\\cyrchar\\cyromegarnd ",
        u"\u047C": "\\cyrchar\\CYROMEGATITLO ",
        u"\u047D": "\\cyrchar\\cyromegatitlo ",
        u"\u047E": "\\cyrchar\\CYROT ",
        u"\u047F": "\\cyrchar\\cyrot ",
        u"\u0480": "\\cyrchar\\CYRKOPPA ",
        u"\u0481": "\\cyrchar\\cyrkoppa ",
        u"\u0482": "\\cyrchar\\cyrthousands ",
        u"\u0488": "\\cyrchar\\cyrhundredthousands ",
        u"\u0489": "\\cyrchar\\cyrmillions ",
        u"\u048C": "\\cyrchar\\CYRSEMISFTSN ",
        u"\u048D": "\\cyrchar\\cyrsemisftsn ",
        u"\u048E": "\\cyrchar\\CYRRTICK ",
        u"\u048F": "\\cyrchar\\cyrrtick ",
        u"\u0490": "\\cyrchar\\CYRGUP ",
        u"\u0491": "\\cyrchar\\cyrgup ",
        u"\u0492": "\\cyrchar\\CYRGHCRS ",
        u"\u0493": "\\cyrchar\\cyrghcrs ",
        u"\u0494": "\\cyrchar\\CYRGHK ",
        u"\u0495": "\\cyrchar\\cyrghk ",
        u"\u0496": "\\cyrchar\\CYRZHDSC ",
        u"\u0497": "\\cyrchar\\cyrzhdsc ",
        u"\u0498": "\\cyrchar\\CYRZDSC ",
        u"\u0499": "\\cyrchar\\cyrzdsc ",
        u"\u049A": "\\cyrchar\\CYRKDSC ",
        u"\u049B": "\\cyrchar\\cyrkdsc ",
        u"\u049C": "\\cyrchar\\CYRKVCRS ",
        u"\u049D": "\\cyrchar\\cyrkvcrs ",
        u"\u049E": "\\cyrchar\\CYRKHCRS ",
        u"\u049F": "\\cyrchar\\cyrkhcrs ",
        u"\u04A0": "\\cyrchar\\CYRKBEAK ",
        u"\u04A1": "\\cyrchar\\cyrkbeak ",
        u"\u04A2": "\\cyrchar\\CYRNDSC ",
        u"\u04A3": "\\cyrchar\\cyrndsc ",
        u"\u04A4": "\\cyrchar\\CYRNG ",
        u"\u04A5": "\\cyrchar\\cyrng ",
        u"\u04A6": "\\cyrchar\\CYRPHK ",
        u"\u04A7": "\\cyrchar\\cyrphk ",
        u"\u04A8": "\\cyrchar\\CYRABHHA ",
        u"\u04A9": "\\cyrchar\\cyrabhha ",
        u"\u04AA": "\\cyrchar\\CYRSDSC ",
        u"\u04AB": "\\cyrchar\\cyrsdsc ",
        u"\u04AC": "\\cyrchar\\CYRTDSC ",
        u"\u04AD": "\\cyrchar\\cyrtdsc ",
        u"\u04AE": "\\cyrchar\\CYRY ",
        u"\u04AF": "\\cyrchar\\cyry ",
        u"\u04B0": "\\cyrchar\\CYRYHCRS ",
        u"\u04B1": "\\cyrchar\\cyryhcrs ",
        u"\u04B2": "\\cyrchar\\CYRHDSC ",
        u"\u04B3": "\\cyrchar\\cyrhdsc ",
        u"\u04B4": "\\cyrchar\\CYRTETSE ",
        u"\u04B5": "\\cyrchar\\cyrtetse ",
        u"\u04B6": "\\cyrchar\\CYRCHRDSC ",
        u"\u04B7": "\\cyrchar\\cyrchrdsc ",
        u"\u04B8": "\\cyrchar\\CYRCHVCRS ",
        u"\u04B9": "\\cyrchar\\cyrchvcrs ",
        u"\u04BA": "\\cyrchar\\CYRSHHA ",
        u"\u04BB": "\\cyrchar\\cyrshha ",
        u"\u04BC": "\\cyrchar\\CYRABHCH ",
        u"\u04BD": "\\cyrchar\\cyrabhch ",
        u"\u04BE": "\\cyrchar\\CYRABHCHDSC ",
        u"\u04BF": "\\cyrchar\\cyrabhchdsc ",
        u"\u04C0": "\\cyrchar\\CYRpalochka ",
        u"\u04C3": "\\cyrchar\\CYRKHK ",
        u"\u04C4": "\\cyrchar\\cyrkhk ",
        u"\u04C7": "\\cyrchar\\CYRNHK ",
        u"\u04C8": "\\cyrchar\\cyrnhk ",
        u"\u04CB": "\\cyrchar\\CYRCHLDSC ",
        u"\u04CC": "\\cyrchar\\cyrchldsc ",
        u"\u04D4": "\\cyrchar\\CYRAE ",
        u"\u04D5": "\\cyrchar\\cyrae ",
        u"\u04D8": "\\cyrchar\\CYRSCHWA ",
        u"\u04D9": "\\cyrchar\\cyrschwa ",
        u"\u04E0": "\\cyrchar\\CYRABHDZE ",
        u"\u04E1": "\\cyrchar\\cyrabhdze ",
        u"\u04E8": "\\cyrchar\\CYROTLD ",
        u"\u04E9": "\\cyrchar\\cyrotld ",
        u"\u2002": "\\hspace{0.6em}",
        u"\u2003": "\\hspace{1em}",
        u"\u2004": "\\hspace{0.33em}",
        u"\u2005": "\\hspace{0.25em}",
        u"\u2006": "\\hspace{0.166em}",
        u"\u2007": "\\hphantom{0}",
        u"\u2008": "\\hphantom{,}",
        u"\u2009": "\\hspace{0.167em}",
        u"\u2009-0200A-0200A": "\\;",
        u"\u200A": "\\mkern1mu ",
        u"\u2013": "\\textendash ",
        u"\u2014": "\\textemdash ",
        u"\u2015": "\\rule{1em}{1pt}",
        u"\u2016": "\\Vert ",
        u"\u201B": "\\Elzreapos ",
        u"\u201C": "\\textquotedblleft ",
        u"\u201D": "\\textquotedblright ",
        u"\u201E": ",,",
        u"\u2020": "\\textdagger ",
        u"\u2021": "\\textdaggerdbl ",
        u"\u2022": "\\textbullet ",
#        u"\u2025": "..",
        u"\u2026": "\\ldots ",
        u"\u2030": "\\textperthousand ",
        u"\u2031": "\\textpertenthousand ",
        u"\u2032": "{'}",
        u"\u2033": "{''}",
        u"\u2034": "{'''}",
        u"\u2035": "\\backprime ",
        u"\u2039": "\\guilsinglleft ",
        u"\u203A": "\\guilsinglright ",
        u"\u2057": "''''",
        u"\u205F": "\\mkern4mu ",
        u"\u2060": "\\nolinebreak ",
        u"\u20A7": "\\ensuremath{\\Elzpes}",
        u"\u20AC": "\\mbox{\\texteuro} ",
        u"\u20DB": "\\dddot ",
        u"\u20DC": "\\ddddot ",
        u"\u2102": "\\mathbb{C}",
        u"\u210A": "\\mathscr{g}",
        u"\u210B": "\\mathscr{H}",
        u"\u210C": "\\mathfrak{H}",
        u"\u210D": "\\mathbb{H}",
        u"\u210F": "\\hslash ",
        u"\u2110": "\\mathscr{I}",
        u"\u2111": "\\mathfrak{I}",
        u"\u2112": "\\mathscr{L}",
        u"\u2113": "\\mathscr{l}",
        u"\u2115": "\\mathbb{N}",
        u"\u2116": "\\cyrchar\\textnumero ",
        u"\u2118": "\\wp ",
        u"\u2119": "\\mathbb{P}",
        u"\u211A": "\\mathbb{Q}",
        u"\u211B": "\\mathscr{R}",
        u"\u211C": "\\mathfrak{R}",
        u"\u211D": "\\mathbb{R}",
        u"\u211E": "\\Elzxrat ",
        u"\u2122": "\\texttrademark ",
        u"\u2124": "\\mathbb{Z}",
        u"\u2126": "\\Omega ",
        u"\u2127": "\\mho ",
        u"\u2128": "\\mathfrak{Z}",
        u"\u2129": "\\ElsevierGlyph{2129}",
        u"\u212B": "\\AA ",
        u"\u212C": "\\mathscr{B}",
        u"\u212D": "\\mathfrak{C}",
        u"\u212F": "\\mathscr{e}",
        u"\u2130": "\\mathscr{E}",
        u"\u2131": "\\mathscr{F}",
        u"\u2133": "\\mathscr{M}",
        u"\u2134": "\\mathscr{o}",
        u"\u2135": "\\aleph ",
        u"\u2136": "\\beth ",
        u"\u2137": "\\gimel ",
        u"\u2138": "\\daleth ",
        u"\u2153": "\\textfrac{1}{3}",
        u"\u2154": "\\textfrac{2}{3}",
        u"\u2155": "\\textfrac{1}{5}",
        u"\u2156": "\\textfrac{2}{5}",
        u"\u2157": "\\textfrac{3}{5}",
        u"\u2158": "\\textfrac{4}{5}",
        u"\u2159": "\\textfrac{1}{6}",
        u"\u215A": "\\textfrac{5}{6}",
        u"\u215B": "\\textfrac{1}{8}",
        u"\u215C": "\\textfrac{3}{8}",
        u"\u215D": "\\textfrac{5}{8}",
        u"\u215E": "\\textfrac{7}{8}",
        u"\u2190": "\\leftarrow ",
        u"\u2191": "\\uparrow ",
        u"\u2192": "\\rightarrow ",
        u"\u2193": "\\downarrow ",
        u"\u2194": "\\leftrightarrow ",
        u"\u2195": "\\updownarrow ",
        u"\u2196": "\\nwarrow ",
        u"\u2197": "\\nearrow ",
        u"\u2198": "\\searrow ",
        u"\u2199": "\\swarrow ",
        u"\u219A": "\\nleftarrow ",
        u"\u219B": "\\nrightarrow ",
        u"\u219C": "\\arrowwaveright ",
        u"\u219D": "\\arrowwaveright ",
        u"\u219E": "\\twoheadleftarrow ",
        u"\u21A0": "\\twoheadrightarrow ",
        u"\u21A2": "\\leftarrowtail ",
        u"\u21A3": "\\rightarrowtail ",
        u"\u21A6": "\\mapsto ",
        u"\u21A9": "\\hookleftarrow ",
        u"\u21AA": "\\hookrightarrow ",
        u"\u21AB": "\\looparrowleft ",
        u"\u21AC": "\\looparrowright ",
        u"\u21AD": "\\leftrightsquigarrow ",
        u"\u21AE": "\\nleftrightarrow ",
        u"\u21B0": "\\Lsh ",
        u"\u21B1": "\\Rsh ",
        u"\u21B3": "\\ElsevierGlyph{21B3}",
        u"\u21B6": "\\curvearrowleft ",
        u"\u21B7": "\\curvearrowright ",
        u"\u21BA": "\\circlearrowleft ",
        u"\u21BB": "\\circlearrowright ",
        u"\u21BC": "\\leftharpoonup ",
        u"\u21BD": "\\leftharpoondown ",
        u"\u21BE": "\\upharpoonright ",
        u"\u21BF": "\\upharpoonleft ",
        u"\u21C0": "\\rightharpoonup ",
        u"\u21C1": "\\rightharpoondown ",
        u"\u21C2": "\\downharpoonright ",
        u"\u21C3": "\\downharpoonleft ",
        u"\u21C4": "\\rightleftarrows ",
        u"\u21C5": "\\dblarrowupdown ",
        u"\u21C6": "\\leftrightarrows ",
        u"\u21C7": "\\leftleftarrows ",
        u"\u21C8": "\\upuparrows ",
        u"\u21C9": "\\rightrightarrows ",
        u"\u21CA": "\\downdownarrows ",
        u"\u21CB": "\\leftrightharpoons ",
        u"\u21CC": "\\rightleftharpoons ",
        u"\u21CD": "\\nLeftarrow ",
        u"\u21CE": "\\nLeftrightarrow ",
        u"\u21CF": "\\nRightarrow ",
        u"\u21D0": "\\Leftarrow ",
        u"\u21D1": "\\Uparrow ",
        u"\u21D2": "\\Rightarrow ",
        u"\u21D3": "\\Downarrow ",
        u"\u21D4": "\\Leftrightarrow ",
        u"\u21D5": "\\Updownarrow ",
        u"\u21DA": "\\Lleftarrow ",
        u"\u21DB": "\\Rrightarrow ",
        u"\u21DD": "\\rightsquigarrow ",
        u"\u21F5": "\\DownArrowUpArrow ",
        u"\u2200": "\\forall ",
        u"\u2201": "\\complement ",
        u"\u2202": "\\partial ",
        u"\u2203": "\\exists ",
        u"\u2204": "\\nexists ",
        u"\u2205": "\\varnothing ",
        u"\u2207": "\\nabla ",
        u"\u2208": "\\in ",
        u"\u2209": "\\not\\in ",
        u"\u220B": "\\ni ",
        u"\u220C": "\\not\\ni ",
        u"\u220F": "\\prod ",
        u"\u2210": "\\coprod ",
        u"\u2211": "\\sum ",
        u"\u2213": "\\mp ",
        u"\u2214": "\\dotplus ",
        u"\u2216": "\\setminus ",
        u"\u2217": "{_\\ast}",
        u"\u2218": "\\circ ",
        u"\u2219": "\\bullet ",
        u"\u221A": "\\surd ",
        u"\u221D": "\\propto ",
        u"\u221E": "\\infty ",
        u"\u221F": "\\rightangle ",
        u"\u2220": "\\angle ",
        u"\u2221": "\\measuredangle ",
        u"\u2222": "\\sphericalangle ",
        u"\u2223": "\\mid ",
        u"\u2224": "\\nmid ",
        u"\u2225": "\\parallel ",
        u"\u2226": "\\nparallel ",
        u"\u2227": "\\wedge ",
        u"\u2228": "\\vee ",
        u"\u2229": "\\cap ",
        u"\u222A": "\\cup ",
        u"\u222B": "\\int ",
        u"\u222C": "\\int\\!\\int ",
        u"\u222D": "\\int\\!\\int\\!\\int ",
        u"\u222E": "\\oint ",
        u"\u222F": "\\surfintegral ",
        u"\u2230": "\\volintegral ",
        u"\u2231": "\\clwintegral ",
        u"\u2232": "\\ElsevierGlyph{2232}",
        u"\u2233": "\\ElsevierGlyph{2233}",
        u"\u2234": "\\therefore ",
        u"\u2235": "\\because ",
        u"\u2237": "\\Colon ",
        u"\u2238": "\\ElsevierGlyph{2238}",
        u"\u223A": "\\mathbin{{:}\\!\\!{-}\\!\\!{:}}",
        u"\u223B": "\\homothetic ",
        u"\u223C": "\\sim ",
        u"\u223D": "\\backsim ",
        u"\u223E": "\\lazysinv ",
        u"\u2240": "\\wr ",
        u"\u2241": "\\not\\sim ",
        u"\u2242": "\\ElsevierGlyph{2242}",
        u"\u2242-00338": "\\NotEqualTilde ",
        u"\u2243": "\\simeq ",
        u"\u2244": "\\not\\simeq ",
        u"\u2245": "\\cong ",
        u"\u2246": "\\approxnotequal ",
        u"\u2247": "\\not\\cong ",
        u"\u2248": "\\approx ",
        u"\u2249": "\\not\\approx ",
        u"\u224A": "\\approxeq ",
        u"\u224B": "\\tildetrpl ",
        u"\u224B-00338": "\\not\\apid ",
        u"\u224C": "\\allequal ",
        u"\u224D": "\\asymp ",
        u"\u224E": "\\Bumpeq ",
        u"\u224E-00338": "\\NotHumpDownHump ",
        u"\u224F": "\\bumpeq ",
        u"\u224F-00338": "\\NotHumpEqual ",
        u"\u2250": "\\doteq ",
        u"\u2250-00338": "\\not\\doteq",
        u"\u2251": "\\doteqdot ",
        u"\u2252": "\\fallingdotseq ",
        u"\u2253": "\\risingdotseq ",
        u"\u2254": ":=",
        u"\u2255": "=:",
        u"\u2256": "\\eqcirc ",
        u"\u2257": "\\circeq ",
        u"\u2259": "\\estimates ",
        u"\u225A": "\\ElsevierGlyph{225A}",
        u"\u225B": "\\starequal ",
        u"\u225C": "\\triangleq ",
        u"\u225F": "\\ElsevierGlyph{225F}",
        u"\u2260": "\\not =",
        u"\u2261": "\\equiv ",
        u"\u2262": "\\not\\equiv ",
        u"\u2264": "\\leq ",
        u"\u2265": "\\geq ",
        u"\u2266": "\\leqq ",
        u"\u2267": "\\geqq ",
        u"\u2268": "\\lneqq ",
        u"\u2268-0FE00": "\\lvertneqq ",
        u"\u2269": "\\gneqq ",
        u"\u2269-0FE00": "\\gvertneqq ",
        u"\u226A": "\\ll ",
        u"\u226A-00338": "\\NotLessLess ",
        u"\u226B": "\\gg ",
        u"\u226B-00338": "\\NotGreaterGreater ",
        u"\u226C": "\\between ",
        u"\u226D": "\\not\\kern-0.3em\\times ",
        u"\u226E": "\\not&lt;",
        u"\u226F": "\\not&gt;",
        u"\u2270": "\\not\\leq ",
        u"\u2271": "\\not\\geq ",
        u"\u2272": "\\lessequivlnt ",
        u"\u2273": "\\greaterequivlnt ",
        u"\u2274": "\\ElsevierGlyph{2274}",
        u"\u2275": "\\ElsevierGlyph{2275}",
        u"\u2276": "\\lessgtr ",
        u"\u2277": "\\gtrless ",
        u"\u2278": "\\notlessgreater ",
        u"\u2279": "\\notgreaterless ",
        u"\u227A": "\\prec ",
        u"\u227B": "\\succ ",
        u"\u227C": "\\preccurlyeq ",
        u"\u227D": "\\succcurlyeq ",
        u"\u227E": "\\precapprox ",
        u"\u227E-00338": "\\NotPrecedesTilde ",
        u"\u227F": "\\succapprox ",
        u"\u227F-00338": "\\NotSucceedsTilde ",
        u"\u2280": "\\not\\prec ",
        u"\u2281": "\\not\\succ ",
        u"\u2282": "\\subset ",
        u"\u2283": "\\supset ",
        u"\u2284": "\\not\\subset ",
        u"\u2285": "\\not\\supset ",
        u"\u2286": "\\subseteq ",
        u"\u2287": "\\supseteq ",
        u"\u2288": "\\not\\subseteq ",
        u"\u2289": "\\not\\supseteq ",
        u"\u228A": "\\subsetneq ",
        u"\u228A-0FE00": "\\varsubsetneqq ",
        u"\u228B": "\\supsetneq ",
        u"\u228B-0FE00": "\\varsupsetneq ",
        u"\u228E": "\\uplus ",
        u"\u228F": "\\sqsubset ",
        u"\u228F-00338": "\\NotSquareSubset ",
        u"\u2290": "\\sqsupset ",
        u"\u2290-00338": "\\NotSquareSuperset ",
        u"\u2291": "\\sqsubseteq ",
        u"\u2292": "\\sqsupseteq ",
        u"\u2293": "\\sqcap ",
        u"\u2294": "\\sqcup ",
        u"\u2295": "\\oplus ",
        u"\u2296": "\\ominus ",
        u"\u2297": "\\otimes ",
        u"\u2298": "\\oslash ",
        u"\u2299": "\\odot ",
        u"\u229A": "\\circledcirc ",
        u"\u229B": "\\circledast ",
        u"\u229D": "\\circleddash ",
        u"\u229E": "\\boxplus ",
        u"\u229F": "\\boxminus ",
        u"\u22A0": "\\boxtimes ",
        u"\u22A1": "\\boxdot ",
        u"\u22A2": "\\vdash ",
        u"\u22A3": "\\dashv ",
        u"\u22A4": "\\top ",
        u"\u22A5": "\\perp ",
        u"\u22A7": "\\truestate ",
        u"\u22A8": "\\forcesextra ",
        u"\u22A9": "\\Vdash ",
        u"\u22AA": "\\Vvdash ",
        u"\u22AB": "\\VDash ",
        u"\u22AC": "\\nvdash ",
        u"\u22AD": "\\nvDash ",
        u"\u22AE": "\\nVdash ",
        u"\u22AF": "\\nVDash ",
        u"\u22B2": "\\vartriangleleft ",
        u"\u22B3": "\\vartriangleright ",
        u"\u22B4": "\\trianglelefteq ",
        u"\u22B5": "\\trianglerighteq ",
        u"\u22B6": "\\original ",
        u"\u22B7": "\\image ",
        u"\u22B8": "\\multimap ",
        u"\u22B9": "\\hermitconjmatrix ",
        u"\u22BA": "\\intercal ",
        u"\u22BB": "\\veebar ",
        u"\u22BE": "\\rightanglearc ",
        u"\u22C0": "\\ElsevierGlyph{22C0}",
        u"\u22C1": "\\ElsevierGlyph{22C1}",
        u"\u22C2": "\\bigcap ",
        u"\u22C3": "\\bigcup ",
        u"\u22C4": "\\diamond ",
        u"\u22C5": "\\cdot ",
        u"\u22C6": "\\star ",
        u"\u22C7": "\\divideontimes ",
        u"\u22C8": "\\bowtie ",
        u"\u22C9": "\\ltimes ",
        u"\u22CA": "\\rtimes ",
        u"\u22CB": "\\leftthreetimes ",
        u"\u22CC": "\\rightthreetimes ",
        u"\u22CD": "\\backsimeq ",
        u"\u22CE": "\\curlyvee ",
        u"\u22CF": "\\curlywedge ",
        u"\u22D0": "\\Subset ",
        u"\u22D1": "\\Supset ",
        u"\u22D2": "\\Cap ",
        u"\u22D3": "\\Cup ",
        u"\u22D4": "\\pitchfork ",
        u"\u22D6": "\\lessdot ",
        u"\u22D7": "\\gtrdot ",
        u"\u22D8": "\\verymuchless ",
        u"\u22D9": "\\verymuchgreater ",
        u"\u22DA": "\\lesseqgtr ",
        u"\u22DB": "\\gtreqless ",
        u"\u22DE": "\\curlyeqprec ",
        u"\u22DF": "\\curlyeqsucc ",
        u"\u22E2": "\\not\\sqsubseteq ",
        u"\u22E3": "\\not\\sqsupseteq ",
        u"\u22E5": "\\Elzsqspne ",
        u"\u22E6": "\\lnsim ",
        u"\u22E7": "\\gnsim ",
        u"\u22E8": "\\precedesnotsimilar ",
        u"\u22E9": "\\succnsim ",
        u"\u22EA": "\\ntriangleleft ",
        u"\u22EB": "\\ntriangleright ",
        u"\u22EC": "\\ntrianglelefteq ",
        u"\u22ED": "\\ntrianglerighteq ",
        u"\u22EE": "\\vdots ",
        u"\u22EF": "\\cdots ",
        u"\u22F0": "\\upslopeellipsis ",
        u"\u22F1": "\\downslopeellipsis ",
        u"\u2305": "\\barwedge ",
        u"\u2306": "\\perspcorrespond ",
        u"\u2308": "\\lceil ",
        u"\u2309": "\\rceil ",
        u"\u230A": "\\lfloor ",
        u"\u230B": "\\rfloor ",
        u"\u2315": "\\recorder ",
        u"\u2316": "\\mathchar\"2208",
        u"\u231C": "\\ulcorner ",
        u"\u231D": "\\urcorner ",
        u"\u231E": "\\llcorner ",
        u"\u231F": "\\lrcorner ",
        u"\u2322": "\\frown ",
        u"\u2323": "\\smile ",
        u"\u2329": "\\langle ",
        u"\u232A": "\\rangle ",
        u"\u233D": "\\ElsevierGlyph{E838}",
        u"\u23A3": "\\Elzdlcorn ",
        u"\u23B0": "\\lmoustache ",
        u"\u23B1": "\\rmoustache ",
        u"\u2423": "\\textvisiblespace ",
        u"\u2460": "\\ding{172}",
        u"\u2461": "\\ding{173}",
        u"\u2462": "\\ding{174}",
        u"\u2463": "\\ding{175}",
        u"\u2464": "\\ding{176}",
        u"\u2465": "\\ding{177}",
        u"\u2466": "\\ding{178}",
        u"\u2467": "\\ding{179}",
        u"\u2468": "\\ding{180}",
        u"\u2469": "\\ding{181}",
        u"\u24C8": "\\circledS ",
        u"\u2506": "\\Elzdshfnc ",
        u"\u2519": "\\Elzsqfnw ",
        u"\u2571": "\\diagup ",
        u"\u25A0": "\\ding{110}",
        u"\u25A1": "\\square ",
        u"\u25AA": "\\blacksquare ",
        u"\u25AD": "\\fbox{~~}",
        u"\u25AF": "\\Elzvrecto ",
        u"\u25B1": "\\ElsevierGlyph{E381}",
        u"\u25B2": "\\ding{115}",
        u"\u25B3": "\\bigtriangleup ",
        u"\u25B4": "\\blacktriangle ",
        u"\u25B5": "\\vartriangle ",
        u"\u25B8": "\\blacktriangleright ",
        u"\u25B9": "\\triangleright ",
        u"\u25BC": "\\ding{116}",
        u"\u25BD": "\\bigtriangledown ",
        u"\u25BE": "\\blacktriangledown ",
        u"\u25BF": "\\triangledown ",
        u"\u25C2": "\\blacktriangleleft ",
        u"\u25C3": "\\triangleleft ",
        u"\u25C6": "\\ding{117}",
        u"\u25CA": "\\lozenge ",
        u"\u25CB": "\\bigcirc ",
        u"\u25CF": "\\ding{108}",
        u"\u25D0": "\\Elzcirfl ",
        u"\u25D1": "\\Elzcirfr ",
        u"\u25D2": "\\Elzcirfb ",
        u"\u25D7": "\\ding{119}",
        u"\u25D8": "\\Elzrvbull ",
        u"\u25E7": "\\Elzsqfl ",
        u"\u25E8": "\\Elzsqfr ",
        u"\u25EA": "\\Elzsqfse ",
        u"\u25EF": "\\bigcirc ",
        u"\u2605": "\\ding{72}",
        u"\u2606": "\\ding{73}",
        u"\u260E": "\\ding{37}",
        u"\u261B": "\\ding{42}",
        u"\u261E": "\\ding{43}",
        u"\u263E": "\\rightmoon ",
        u"\u263F": "\\mercury ",
        u"\u2640": "\\venus ",
        u"\u2642": "\\male ",
        u"\u2643": "\\jupiter ",
        u"\u2644": "\\saturn ",
        u"\u2645": "\\uranus ",
        u"\u2646": "\\neptune ",
        u"\u2647": "\\pluto ",
        u"\u2648": "\\aries ",
        u"\u2649": "\\taurus ",
        u"\u264A": "\\gemini ",
        u"\u264B": "\\cancer ",
        u"\u264C": "\\leo ",
        u"\u264D": "\\virgo ",
        u"\u264E": "\\libra ",
        u"\u264F": "\\scorpio ",
        u"\u2650": "\\sagittarius ",
        u"\u2651": "\\capricornus ",
        u"\u2652": "\\aquarius ",
        u"\u2653": "\\pisces ",
        u"\u2660": "\\ding{171}",
        u"\u2662": "\\diamond ",
        u"\u2663": "\\ding{168}",
        u"\u2665": "\\ding{170}",
        u"\u2666": "\\ding{169}",
        u"\u2669": "\\quarternote ",
        u"\u266A": "\\eighthnote ",
        u"\u266D": "\\flat ",
        u"\u266E": "\\natural ",
        u"\u266F": "\\sharp ",
        u"\u2701": "\\ding{33}",
        u"\u2702": "\\ding{34}",
        u"\u2703": "\\ding{35}",
        u"\u2704": "\\ding{36}",
        u"\u2706": "\\ding{38}",
        u"\u2707": "\\ding{39}",
        u"\u2708": "\\ding{40}",
        u"\u2709": "\\ding{41}",
        u"\u270C": "\\ding{44}",
        u"\u270D": "\\ding{45}",
        u"\u270E": "\\ding{46}",
        u"\u270F": "\\ding{47}",
        u"\u2710": "\\ding{48}",
        u"\u2711": "\\ding{49}",
        u"\u2712": "\\ding{50}",
        u"\u2713": "\\ding{51}",
        u"\u2714": "\\ding{52}",
        u"\u2715": "\\ding{53}",
        u"\u2716": "\\ding{54}",
        u"\u2717": "\\ding{55}",
        u"\u2718": "\\ding{56}",
        u"\u2719": "\\ding{57}",
        u"\u271A": "\\ding{58}",
        u"\u271B": "\\ding{59}",
        u"\u271C": "\\ding{60}",
        u"\u271D": "\\ding{61}",
        u"\u271E": "\\ding{62}",
        u"\u271F": "\\ding{63}",
        u"\u2720": "\\ding{64}",
        u"\u2721": "\\ding{65}",
        u"\u2722": "\\ding{66}",
        u"\u2723": "\\ding{67}",
        u"\u2724": "\\ding{68}",
        u"\u2725": "\\ding{69}",
        u"\u2726": "\\ding{70}",
        u"\u2727": "\\ding{71}",
        u"\u2729": "\\ding{73}",
        u"\u272A": "\\ding{74}",
        u"\u272B": "\\ding{75}",
        u"\u272C": "\\ding{76}",
        u"\u272D": "\\ding{77}",
        u"\u272E": "\\ding{78}",
        u"\u272F": "\\ding{79}",
        u"\u2730": "\\ding{80}",
        u"\u2731": "\\ding{81}",
        u"\u2732": "\\ding{82}",
        u"\u2733": "\\ding{83}",
        u"\u2734": "\\ding{84}",
        u"\u2735": "\\ding{85}",
        u"\u2736": "\\ding{86}",
        u"\u2737": "\\ding{87}",
        u"\u2738": "\\ding{88}",
        u"\u2739": "\\ding{89}",
        u"\u273A": "\\ding{90}",
        u"\u273B": "\\ding{91}",
        u"\u273C": "\\ding{92}",
        u"\u273D": "\\ding{93}",
        u"\u273E": "\\ding{94}",
        u"\u273F": "\\ding{95}",
        u"\u2740": "\\ding{96}",
        u"\u2741": "\\ding{97}",
        u"\u2742": "\\ding{98}",
        u"\u2743": "\\ding{99}",
        u"\u2744": "\\ding{100}",
        u"\u2745": "\\ding{101}",
        u"\u2746": "\\ding{102}",
        u"\u2747": "\\ding{103}",
        u"\u2748": "\\ding{104}",
        u"\u2749": "\\ding{105}",
        u"\u274A": "\\ding{106}",
        u"\u274B": "\\ding{107}",
        u"\u274D": "\\ding{109}",
        u"\u274F": "\\ding{111}",
        u"\u2750": "\\ding{112}",
        u"\u2751": "\\ding{113}",
        u"\u2752": "\\ding{114}",
        u"\u2756": "\\ding{118}",
        u"\u2758": "\\ding{120}",
        u"\u2759": "\\ding{121}",
        u"\u275A": "\\ding{122}",
        u"\u275B": "\\ding{123}",
        u"\u275C": "\\ding{124}",
        u"\u275D": "\\ding{125}",
        u"\u275E": "\\ding{126}",
        u"\u2761": "\\ding{161}",
        u"\u2762": "\\ding{162}",
        u"\u2763": "\\ding{163}",
        u"\u2764": "\\ding{164}",
        u"\u2765": "\\ding{165}",
        u"\u2766": "\\ding{166}",
        u"\u2767": "\\ding{167}",
        u"\u2776": "\\ding{182}",
        u"\u2777": "\\ding{183}",
        u"\u2778": "\\ding{184}",
        u"\u2779": "\\ding{185}",
        u"\u277A": "\\ding{186}",
        u"\u277B": "\\ding{187}",
        u"\u277C": "\\ding{188}",
        u"\u277D": "\\ding{189}",
        u"\u277E": "\\ding{190}",
        u"\u277F": "\\ding{191}",
        u"\u2780": "\\ding{192}",
        u"\u2781": "\\ding{193}",
        u"\u2782": "\\ding{194}",
        u"\u2783": "\\ding{195}",
        u"\u2784": "\\ding{196}",
        u"\u2785": "\\ding{197}",
        u"\u2786": "\\ding{198}",
        u"\u2787": "\\ding{199}",
        u"\u2788": "\\ding{200}",
        u"\u2789": "\\ding{201}",
        u"\u278A": "\\ding{202}",
        u"\u278B": "\\ding{203}",
        u"\u278C": "\\ding{204}",
        u"\u278D": "\\ding{205}",
        u"\u278E": "\\ding{206}",
        u"\u278F": "\\ding{207}",
        u"\u2790": "\\ding{208}",
        u"\u2791": "\\ding{209}",
        u"\u2792": "\\ding{210}",
        u"\u2793": "\\ding{211}",
        u"\u2794": "\\ding{212}",
        u"\u2798": "\\ding{216}",
        u"\u2799": "\\ding{217}",
        u"\u279A": "\\ding{218}",
        u"\u279B": "\\ding{219}",
        u"\u279C": "\\ding{220}",
        u"\u279D": "\\ding{221}",
        u"\u279E": "\\ding{222}",
        u"\u279F": "\\ding{223}",
        u"\u27A0": "\\ding{224}",
        u"\u27A1": "\\ding{225}",
        u"\u27A2": "\\ding{226}",
        u"\u27A3": "\\ding{227}",
        u"\u27A4": "\\ding{228}",
        u"\u27A5": "\\ding{229}",
        u"\u27A6": "\\ding{230}",
        u"\u27A7": "\\ding{231}",
        u"\u27A8": "\\ding{232}",
        u"\u27A9": "\\ding{233}",
        u"\u27AA": "\\ding{234}",
        u"\u27AB": "\\ding{235}",
        u"\u27AC": "\\ding{236}",
        u"\u27AD": "\\ding{237}",
        u"\u27AE": "\\ding{238}",
        u"\u27AF": "\\ding{239}",
        u"\u27B1": "\\ding{241}",
        u"\u27B2": "\\ding{242}",
        u"\u27B3": "\\ding{243}",
        u"\u27B4": "\\ding{244}",
        u"\u27B5": "\\ding{245}",
        u"\u27B6": "\\ding{246}",
        u"\u27B7": "\\ding{247}",
        u"\u27B8": "\\ding{248}",
        u"\u27B9": "\\ding{249}",
        u"\u27BA": "\\ding{250}",
        u"\u27BB": "\\ding{251}",
        u"\u27BC": "\\ding{252}",
        u"\u27BD": "\\ding{253}",
        u"\u27BE": "\\ding{254}",
        u"\u27F5": "\\longleftarrow ",
        u"\u27F6": "\\longrightarrow ",
        u"\u27F7": "\\longleftrightarrow ",
        u"\u27F8": "\\Longleftarrow ",
        u"\u27F9": "\\Longrightarrow ",
        u"\u27FA": "\\Longleftrightarrow ",
        u"\u27FC": "\\longmapsto ",
        u"\u27FF": "\\sim\\joinrel\\leadsto",
        u"\u2905": "\\ElsevierGlyph{E212}",
        u"\u2912": "\\UpArrowBar ",
        u"\u2913": "\\DownArrowBar ",
        u"\u2923": "\\ElsevierGlyph{E20C}",
        u"\u2924": "\\ElsevierGlyph{E20D}",
        u"\u2925": "\\ElsevierGlyph{E20B}",
        u"\u2926": "\\ElsevierGlyph{E20A}",
        u"\u2927": "\\ElsevierGlyph{E211}",
        u"\u2928": "\\ElsevierGlyph{E20E}",
        u"\u2929": "\\ElsevierGlyph{E20F}",
        u"\u292A": "\\ElsevierGlyph{E210}",
        u"\u2933": "\\ElsevierGlyph{E21C}",
        u"\u2933-00338": "\\ElsevierGlyph{E21D}",
        u"\u2936": "\\ElsevierGlyph{E21A}",
        u"\u2937": "\\ElsevierGlyph{E219}",
        u"\u2940": "\\Elolarr ",
        u"\u2941": "\\Elorarr ",
        u"\u2942": "\\ElzRlarr ",
        u"\u2944": "\\ElzrLarr ",
        u"\u2947": "\\Elzrarrx ",
        u"\u294E": "\\LeftRightVector ",
        u"\u294F": "\\RightUpDownVector ",
        u"\u2950": "\\DownLeftRightVector ",
        u"\u2951": "\\LeftUpDownVector ",
        u"\u2952": "\\LeftVectorBar ",
        u"\u2953": "\\RightVectorBar ",
        u"\u2954": "\\RightUpVectorBar ",
        u"\u2955": "\\RightDownVectorBar ",
        u"\u2956": "\\DownLeftVectorBar ",
        u"\u2957": "\\DownRightVectorBar ",
        u"\u2958": "\\LeftUpVectorBar ",
        u"\u2959": "\\LeftDownVectorBar ",
        u"\u295A": "\\LeftTeeVector ",
        u"\u295B": "\\RightTeeVector ",
        u"\u295C": "\\RightUpTeeVector ",
        u"\u295D": "\\RightDownTeeVector ",
        u"\u295E": "\\DownLeftTeeVector ",
        u"\u295F": "\\DownRightTeeVector ",
        u"\u2960": "\\LeftUpTeeVector ",
        u"\u2961": "\\LeftDownTeeVector ",
        u"\u296E": "\\UpEquilibrium ",
        u"\u296F": "\\ReverseUpEquilibrium ",
        u"\u2970": "\\RoundImplies ",
        u"\u297C": "\\ElsevierGlyph{E214}",
        u"\u297D": "\\ElsevierGlyph{E215}",
        u"\u2980": "\\Elztfnc ",
        u"\u2985": "\\ElsevierGlyph{3018}",
        u"\u2986": "\\Elroang ",
        u"\u2993": "&lt;\\kern-0.58em(",
        u"\u2994": "\\ElsevierGlyph{E291}",
        u"\u2999": "\\Elzddfnc ",
        u"\u299C": "\\Angle ",
        u"\u29A0": "\\Elzlpargt ",
        u"\u29B5": "\\ElsevierGlyph{E260}",
        u"\u29B6": "\\ElsevierGlyph{E61B}",
        u"\u29CA": "\\ElzLap ",
        u"\u29CB": "\\Elzdefas ",
        u"\u29CF": "\\LeftTriangleBar ",
        u"\u29CF-00338": "\\NotLeftTriangleBar ",
        u"\u29D0": "\\RightTriangleBar ",
        u"\u29D0-00338": "\\NotRightTriangleBar ",
        u"\u29DC": "\\ElsevierGlyph{E372}",
        u"\u29EB": "\\blacklozenge ",
        u"\u29F4": "\\RuleDelayed ",
        u"\u2A04": "\\Elxuplus ",
        u"\u2A05": "\\ElzThr ",
        u"\u2A06": "\\Elxsqcup ",
        u"\u2A07": "\\ElzInf ",
        u"\u2A08": "\\ElzSup ",
        u"\u2A0D": "\\ElzCint ",
        u"\u2A0F": "\\clockoint ",
        u"\u2A10": "\\ElsevierGlyph{E395}",
        u"\u2A16": "\\sqrint ",
        u"\u2A25": "\\ElsevierGlyph{E25A}",
        u"\u2A2A": "\\ElsevierGlyph{E25B}",
        u"\u2A2D": "\\ElsevierGlyph{E25C}",
        u"\u2A2E": "\\ElsevierGlyph{E25D}",
        u"\u2A2F": "\\ElzTimes ",
        u"\u2A34": "\\ElsevierGlyph{E25E}",
        u"\u2A35": "\\ElsevierGlyph{E25E}",
        u"\u2A3C": "\\ElsevierGlyph{E259}",
        u"\u2A3F": "\\amalg ",
        u"\u2A53": "\\ElzAnd ",
        u"\u2A54": "\\ElzOr ",
        u"\u2A55": "\\ElsevierGlyph{E36E}",
        u"\u2A56": "\\ElOr ",
        u"\u2A5E": "\\perspcorrespond ",
        u"\u2A5F": "\\Elzminhat ",
        u"\u2A63": "\\ElsevierGlyph{225A}",
        u"\u2A6E": "\\stackrel{*}{=}",
        u"\u2A75": "\\Equal ",
        u"\u2A7D": "\\leqslant ",
        u"\u2A7D-00338": "\\nleqslant ",
        u"\u2A7E": "\\geqslant ",
        u"\u2A7E-00338": "\\ngeqslant ",
        u"\u2A85": "\\lessapprox ",
        u"\u2A86": "\\gtrapprox ",
        u"\u2A87": "\\lneq ",
        u"\u2A88": "\\gneq ",
        u"\u2A89": "\\lnapprox ",
        u"\u2A8A": "\\gnapprox ",
        u"\u2A8B": "\\lesseqqgtr ",
        u"\u2A8C": "\\gtreqqless ",
        u"\u2A95": "\\eqslantless ",
        u"\u2A96": "\\eqslantgtr ",
        u"\u2A9D": "\\Pisymbol{ppi020}{117}",
        u"\u2A9E": "\\Pisymbol{ppi020}{105}",
        u"\u2AA1": "\\NestedLessLess ",
        u"\u2AA1-00338": "\\NotNestedLessLess ",
        u"\u2AA2": "\\NestedGreaterGreater ",
        u"\u2AA2-00338": "\\NotNestedGreaterGreater ",
        u"\u2AAF": "\\preceq ",
        u"\u2AAF-00338": "\\not\\preceq ",
        u"\u2AB0": "\\succeq ",
        u"\u2AB0-00338": "\\not\\succeq ",
        u"\u2AB5": "\\precneqq ",
        u"\u2AB6": "\\succneqq ",
        u"\u2AB7": "\\precapprox ",
        u"\u2AB8": "\\succapprox ",
        u"\u2AB9": "\\precnapprox ",
        u"\u2ABA": "\\succnapprox ",
        u"\u2AC5": "\\subseteqq ",
        u"\u2AC5-00338": "\\nsubseteqq ",
        u"\u2AC6": "\\supseteqq ",
        u"\u2AC6-00338": "\\nsupseteqq",
        u"\u2ACB": "\\subsetneqq ",
        u"\u2ACC": "\\supsetneqq ",
        u"\u2AEB": "\\ElsevierGlyph{E30D}",
        u"\u2AF6": "\\Elztdcol ",
        u"\u2AFD": "{{/}\\!\\!{/}}",
        u"\u2AFD-020E5": "{\\rlap{\\textbackslash}{{/}\\!\\!{/}}}",
        u"\u300A": "\\ElsevierGlyph{300A}",
        u"\u300B": "\\ElsevierGlyph{300B}",
        u"\u3018": "\\ElsevierGlyph{3018}",
        u"\u3019": "\\ElsevierGlyph{3019}",
        u"\u301A": "\\openbracketleft ",
        u"\u301B": "\\openbracketright ",
#        u"\uFB00": "ff",
#        u"\uFB01": "fi",
#        u"\uFB02": "fl",
#        u"\uFB03": "ffi",
#        u"\uFB04": "ffl",
        u"\uD400": "\\mathbf{A}",
        u"\uD401": "\\mathbf{B}",
        u"\uD402": "\\mathbf{C}",
        u"\uD403": "\\mathbf{D}",
        u"\uD404": "\\mathbf{E}",
        u"\uD405": "\\mathbf{F}",
        u"\uD406": "\\mathbf{G}",
        u"\uD407": "\\mathbf{H}",
        u"\uD408": "\\mathbf{I}",
        u"\uD409": "\\mathbf{J}",
        u"\uD40A": "\\mathbf{K}",
        u"\uD40B": "\\mathbf{L}",
        u"\uD40C": "\\mathbf{M}",
        u"\uD40D": "\\mathbf{N}",
        u"\uD40E": "\\mathbf{O}",
        u"\uD40F": "\\mathbf{P}",
        u"\uD410": "\\mathbf{Q}",
        u"\uD411": "\\mathbf{R}",
        u"\uD412": "\\mathbf{S}",
        u"\uD413": "\\mathbf{T}",
        u"\uD414": "\\mathbf{U}",
        u"\uD415": "\\mathbf{V}",
        u"\uD416": "\\mathbf{W}",
        u"\uD417": "\\mathbf{X}",
        u"\uD418": "\\mathbf{Y}",
        u"\uD419": "\\mathbf{Z}",
        u"\uD41A": "\\mathbf{a}",
        u"\uD41B": "\\mathbf{b}",
        u"\uD41C": "\\mathbf{c}",
        u"\uD41D": "\\mathbf{d}",
        u"\uD41E": "\\mathbf{e}",
        u"\uD41F": "\\mathbf{f}",
        u"\uD420": "\\mathbf{g}",
        u"\uD421": "\\mathbf{h}",
        u"\uD422": "\\mathbf{i}",
        u"\uD423": "\\mathbf{j}",
        u"\uD424": "\\mathbf{k}",
        u"\uD425": "\\mathbf{l}",
        u"\uD426": "\\mathbf{m}",
        u"\uD427": "\\mathbf{n}",
        u"\uD428": "\\mathbf{o}",
        u"\uD429": "\\mathbf{p}",
        u"\uD42A": "\\mathbf{q}",
        u"\uD42B": "\\mathbf{r}",
        u"\uD42C": "\\mathbf{s}",
        u"\uD42D": "\\mathbf{t}",
        u"\uD42E": "\\mathbf{u}",
        u"\uD42F": "\\mathbf{v}",
        u"\uD430": "\\mathbf{w}",
        u"\uD431": "\\mathbf{x}",
        u"\uD432": "\\mathbf{y}",
        u"\uD433": "\\mathbf{z}",
        u"\uD434": "\\mathsl{A}",
        u"\uD435": "\\mathsl{B}",
        u"\uD436": "\\mathsl{C}",
        u"\uD437": "\\mathsl{D}",
        u"\uD438": "\\mathsl{E}",
        u"\uD439": "\\mathsl{F}",
        u"\uD43A": "\\mathsl{G}",
        u"\uD43B": "\\mathsl{H}",
        u"\uD43C": "\\mathsl{I}",
        u"\uD43D": "\\mathsl{J}",
        u"\uD43E": "\\mathsl{K}",
        u"\uD43F": "\\mathsl{L}",
        u"\uD440": "\\mathsl{M}",
        u"\uD441": "\\mathsl{N}",
        u"\uD442": "\\mathsl{O}",
        u"\uD443": "\\mathsl{P}",
        u"\uD444": "\\mathsl{Q}",
        u"\uD445": "\\mathsl{R}",
        u"\uD446": "\\mathsl{S}",
        u"\uD447": "\\mathsl{T}",
        u"\uD448": "\\mathsl{U}",
        u"\uD449": "\\mathsl{V}",
        u"\uD44A": "\\mathsl{W}",
        u"\uD44B": "\\mathsl{X}",
        u"\uD44C": "\\mathsl{Y}",
        u"\uD44D": "\\mathsl{Z}",
        u"\uD44E": "\\mathsl{a}",
        u"\uD44F": "\\mathsl{b}",
        u"\uD450": "\\mathsl{c}",
        u"\uD451": "\\mathsl{d}",
        u"\uD452": "\\mathsl{e}",
        u"\uD453": "\\mathsl{f}",
        u"\uD454": "\\mathsl{g}",
        u"\uD456": "\\mathsl{i}",
        u"\uD457": "\\mathsl{j}",
        u"\uD458": "\\mathsl{k}",
        u"\uD459": "\\mathsl{l}",
        u"\uD45A": "\\mathsl{m}",
        u"\uD45B": "\\mathsl{n}",
        u"\uD45C": "\\mathsl{o}",
        u"\uD45D": "\\mathsl{p}",
        u"\uD45E": "\\mathsl{q}",
        u"\uD45F": "\\mathsl{r}",
        u"\uD460": "\\mathsl{s}",
        u"\uD461": "\\mathsl{t}",
        u"\uD462": "\\mathsl{u}",
        u"\uD463": "\\mathsl{v}",
        u"\uD464": "\\mathsl{w}",
        u"\uD465": "\\mathsl{x}",
        u"\uD466": "\\mathsl{y}",
        u"\uD467": "\\mathsl{z}",
        u"\uD468": "\\mathbit{A}",
        u"\uD469": "\\mathbit{B}",
        u"\uD46A": "\\mathbit{C}",
        u"\uD46B": "\\mathbit{D}",
        u"\uD46C": "\\mathbit{E}",
        u"\uD46D": "\\mathbit{F}",
        u"\uD46E": "\\mathbit{G}",
        u"\uD46F": "\\mathbit{H}",
        u"\uD470": "\\mathbit{I}",
        u"\uD471": "\\mathbit{J}",
        u"\uD472": "\\mathbit{K}",
        u"\uD473": "\\mathbit{L}",
        u"\uD474": "\\mathbit{M}",
        u"\uD475": "\\mathbit{N}",
        u"\uD476": "\\mathbit{O}",
        u"\uD477": "\\mathbit{P}",
        u"\uD478": "\\mathbit{Q}",
        u"\uD479": "\\mathbit{R}",
        u"\uD47A": "\\mathbit{S}",
        u"\uD47B": "\\mathbit{T}",
        u"\uD47C": "\\mathbit{U}",
        u"\uD47D": "\\mathbit{V}",
        u"\uD47E": "\\mathbit{W}",
        u"\uD47F": "\\mathbit{X}",
        u"\uD480": "\\mathbit{Y}",
        u"\uD481": "\\mathbit{Z}",
        u"\uD482": "\\mathbit{a}",
        u"\uD483": "\\mathbit{b}",
        u"\uD484": "\\mathbit{c}",
        u"\uD485": "\\mathbit{d}",
        u"\uD486": "\\mathbit{e}",
        u"\uD487": "\\mathbit{f}",
        u"\uD488": "\\mathbit{g}",
        u"\uD489": "\\mathbit{h}",
        u"\uD48A": "\\mathbit{i}",
        u"\uD48B": "\\mathbit{j}",
        u"\uD48C": "\\mathbit{k}",
        u"\uD48D": "\\mathbit{l}",
        u"\uD48E": "\\mathbit{m}",
        u"\uD48F": "\\mathbit{n}",
        u"\uD490": "\\mathbit{o}",
        u"\uD491": "\\mathbit{p}",
        u"\uD492": "\\mathbit{q}",
        u"\uD493": "\\mathbit{r}",
        u"\uD494": "\\mathbit{s}",
        u"\uD495": "\\mathbit{t}",
        u"\uD496": "\\mathbit{u}",
        u"\uD497": "\\mathbit{v}",
        u"\uD498": "\\mathbit{w}",
        u"\uD499": "\\mathbit{x}",
        u"\uD49A": "\\mathbit{y}",
        u"\uD49B": "\\mathbit{z}",
        u"\uD49C": "\\mathscr{A}",
        u"\uD49E": "\\mathscr{C}",
        u"\uD49F": "\\mathscr{D}",
        u"\uD4A2": "\\mathscr{G}",
        u"\uD4A5": "\\mathscr{J}",
        u"\uD4A6": "\\mathscr{K}",
        u"\uD4A9": "\\mathscr{N}",
        u"\uD4AA": "\\mathscr{O}",
        u"\uD4AB": "\\mathscr{P}",
        u"\uD4AC": "\\mathscr{Q}",
        u"\uD4AE": "\\mathscr{S}",
        u"\uD4AF": "\\mathscr{T}",
        u"\uD4B0": "\\mathscr{U}",
        u"\uD4B1": "\\mathscr{V}",
        u"\uD4B2": "\\mathscr{W}",
        u"\uD4B3": "\\mathscr{X}",
        u"\uD4B4": "\\mathscr{Y}",
        u"\uD4B5": "\\mathscr{Z}",
        u"\uD4B6": "\\mathscr{a}",
        u"\uD4B7": "\\mathscr{b}",
        u"\uD4B8": "\\mathscr{c}",
        u"\uD4B9": "\\mathscr{d}",
        u"\uD4BB": "\\mathscr{f}",
        u"\uD4BD": "\\mathscr{h}",
        u"\uD4BE": "\\mathscr{i}",
        u"\uD4BF": "\\mathscr{j}",
        u"\uD4C0": "\\mathscr{k}",
        u"\uD4C1": "\\mathscr{l}",
        u"\uD4C2": "\\mathscr{m}",
        u"\uD4C3": "\\mathscr{n}",
        u"\uD4C5": "\\mathscr{p}",
        u"\uD4C6": "\\mathscr{q}",
        u"\uD4C7": "\\mathscr{r}",
        u"\uD4C8": "\\mathscr{s}",
        u"\uD4C9": "\\mathscr{t}",
        u"\uD4CA": "\\mathscr{u}",
        u"\uD4CB": "\\mathscr{v}",
        u"\uD4CC": "\\mathscr{w}",
        u"\uD4CD": "\\mathscr{x}",
        u"\uD4CE": "\\mathscr{y}",
        u"\uD4CF": "\\mathscr{z}",
        u"\uD4D0": "\\mathmit{A}",
        u"\uD4D1": "\\mathmit{B}",
        u"\uD4D2": "\\mathmit{C}",
        u"\uD4D3": "\\mathmit{D}",
        u"\uD4D4": "\\mathmit{E}",
        u"\uD4D5": "\\mathmit{F}",
        u"\uD4D6": "\\mathmit{G}",
        u"\uD4D7": "\\mathmit{H}",
        u"\uD4D8": "\\mathmit{I}",
        u"\uD4D9": "\\mathmit{J}",
        u"\uD4DA": "\\mathmit{K}",
        u"\uD4DB": "\\mathmit{L}",
        u"\uD4DC": "\\mathmit{M}",
        u"\uD4DD": "\\mathmit{N}",
        u"\uD4DE": "\\mathmit{O}",
        u"\uD4DF": "\\mathmit{P}",
        u"\uD4E0": "\\mathmit{Q}",
        u"\uD4E1": "\\mathmit{R}",
        u"\uD4E2": "\\mathmit{S}",
        u"\uD4E3": "\\mathmit{T}",
        u"\uD4E4": "\\mathmit{U}",
        u"\uD4E5": "\\mathmit{V}",
        u"\uD4E6": "\\mathmit{W}",
        u"\uD4E7": "\\mathmit{X}",
        u"\uD4E8": "\\mathmit{Y}",
        u"\uD4E9": "\\mathmit{Z}",
        u"\uD4EA": "\\mathmit{a}",
        u"\uD4EB": "\\mathmit{b}",
        u"\uD4EC": "\\mathmit{c}",
        u"\uD4ED": "\\mathmit{d}",
        u"\uD4EE": "\\mathmit{e}",
        u"\uD4EF": "\\mathmit{f}",
        u"\uD4F0": "\\mathmit{g}",
        u"\uD4F1": "\\mathmit{h}",
        u"\uD4F2": "\\mathmit{i}",
        u"\uD4F3": "\\mathmit{j}",
        u"\uD4F4": "\\mathmit{k}",
        u"\uD4F5": "\\mathmit{l}",
        u"\uD4F6": "\\mathmit{m}",
        u"\uD4F7": "\\mathmit{n}",
        u"\uD4F8": "\\mathmit{o}",
        u"\uD4F9": "\\mathmit{p}",
        u"\uD4FA": "\\mathmit{q}",
        u"\uD4FB": "\\mathmit{r}",
        u"\uD4FC": "\\mathmit{s}",
        u"\uD4FD": "\\mathmit{t}",
        u"\uD4FE": "\\mathmit{u}",
        u"\uD4FF": "\\mathmit{v}",
        u"\uD500": "\\mathmit{w}",
        u"\uD501": "\\mathmit{x}",
        u"\uD502": "\\mathmit{y}",
        u"\uD503": "\\mathmit{z}",
        u"\uD504": "\\mathfrak{A}",
        u"\uD505": "\\mathfrak{B}",
        u"\uD507": "\\mathfrak{D}",
        u"\uD508": "\\mathfrak{E}",
        u"\uD509": "\\mathfrak{F}",
        u"\uD50A": "\\mathfrak{G}",
        u"\uD50D": "\\mathfrak{J}",
        u"\uD50E": "\\mathfrak{K}",
        u"\uD50F": "\\mathfrak{L}",
        u"\uD510": "\\mathfrak{M}",
        u"\uD511": "\\mathfrak{N}",
        u"\uD512": "\\mathfrak{O}",
        u"\uD513": "\\mathfrak{P}",
        u"\uD514": "\\mathfrak{Q}",
        u"\uD516": "\\mathfrak{S}",
        u"\uD517": "\\mathfrak{T}",
        u"\uD518": "\\mathfrak{U}",
        u"\uD519": "\\mathfrak{V}",
        u"\uD51A": "\\mathfrak{W}",
        u"\uD51B": "\\mathfrak{X}",
        u"\uD51C": "\\mathfrak{Y}",
        u"\uD51E": "\\mathfrak{a}",
        u"\uD51F": "\\mathfrak{b}",
        u"\uD520": "\\mathfrak{c}",
        u"\uD521": "\\mathfrak{d}",
        u"\uD522": "\\mathfrak{e}",
        u"\uD523": "\\mathfrak{f}",
        u"\uD524": "\\mathfrak{g}",
        u"\uD525": "\\mathfrak{h}",
        u"\uD526": "\\mathfrak{i}",
        u"\uD527": "\\mathfrak{j}",
        u"\uD528": "\\mathfrak{k}",
        u"\uD529": "\\mathfrak{l}",
        u"\uD52A": "\\mathfrak{m}",
        u"\uD52B": "\\mathfrak{n}",
        u"\uD52C": "\\mathfrak{o}",
        u"\uD52D": "\\mathfrak{p}",
        u"\uD52E": "\\mathfrak{q}",
        u"\uD52F": "\\mathfrak{r}",
        u"\uD530": "\\mathfrak{s}",
        u"\uD531": "\\mathfrak{t}",
        u"\uD532": "\\mathfrak{u}",
        u"\uD533": "\\mathfrak{v}",
        u"\uD534": "\\mathfrak{w}",
        u"\uD535": "\\mathfrak{x}",
        u"\uD536": "\\mathfrak{y}",
        u"\uD537": "\\mathfrak{z}",
        u"\uD538": "\\mathbb{A}",
        u"\uD539": "\\mathbb{B}",
        u"\uD53B": "\\mathbb{D}",
        u"\uD53C": "\\mathbb{E}",
        u"\uD53D": "\\mathbb{F}",
        u"\uD53E": "\\mathbb{G}",
        u"\uD540": "\\mathbb{I}",
        u"\uD541": "\\mathbb{J}",
        u"\uD542": "\\mathbb{K}",
        u"\uD543": "\\mathbb{L}",
        u"\uD544": "\\mathbb{M}",
        u"\uD546": "\\mathbb{O}",
        u"\uD54A": "\\mathbb{S}",
        u"\uD54B": "\\mathbb{T}",
        u"\uD54C": "\\mathbb{U}",
        u"\uD54D": "\\mathbb{V}",
        u"\uD54E": "\\mathbb{W}",
        u"\uD54F": "\\mathbb{X}",
        u"\uD550": "\\mathbb{Y}",
        u"\uD552": "\\mathbb{a}",
        u"\uD553": "\\mathbb{b}",
        u"\uD554": "\\mathbb{c}",
        u"\uD555": "\\mathbb{d}",
        u"\uD556": "\\mathbb{e}",
        u"\uD557": "\\mathbb{f}",
        u"\uD558": "\\mathbb{g}",
        u"\uD559": "\\mathbb{h}",
        u"\uD55A": "\\mathbb{i}",
        u"\uD55B": "\\mathbb{j}",
        u"\uD55C": "\\mathbb{k}",
        u"\uD55D": "\\mathbb{l}",
        u"\uD55E": "\\mathbb{m}",
        u"\uD55F": "\\mathbb{n}",
        u"\uD560": "\\mathbb{o}",
        u"\uD561": "\\mathbb{p}",
        u"\uD562": "\\mathbb{q}",
        u"\uD563": "\\mathbb{r}",
        u"\uD564": "\\mathbb{s}",
        u"\uD565": "\\mathbb{t}",
        u"\uD566": "\\mathbb{u}",
        u"\uD567": "\\mathbb{v}",
        u"\uD568": "\\mathbb{w}",
        u"\uD569": "\\mathbb{x}",
        u"\uD56A": "\\mathbb{y}",
        u"\uD56B": "\\mathbb{z}",
        u"\uD56C": "\\mathslbb{A}",
        u"\uD56D": "\\mathslbb{B}",
        u"\uD56E": "\\mathslbb{C}",
        u"\uD56F": "\\mathslbb{D}",
        u"\uD570": "\\mathslbb{E}",
        u"\uD571": "\\mathslbb{F}",
        u"\uD572": "\\mathslbb{G}",
        u"\uD573": "\\mathslbb{H}",
        u"\uD574": "\\mathslbb{I}",
        u"\uD575": "\\mathslbb{J}",
        u"\uD576": "\\mathslbb{K}",
        u"\uD577": "\\mathslbb{L}",
        u"\uD578": "\\mathslbb{M}",
        u"\uD579": "\\mathslbb{N}",
        u"\uD57A": "\\mathslbb{O}",
        u"\uD57B": "\\mathslbb{P}",
        u"\uD57C": "\\mathslbb{Q}",
        u"\uD57D": "\\mathslbb{R}",
        u"\uD57E": "\\mathslbb{S}",
        u"\uD57F": "\\mathslbb{T}",
        u"\uD580": "\\mathslbb{U}",
        u"\uD581": "\\mathslbb{V}",
        u"\uD582": "\\mathslbb{W}",
        u"\uD583": "\\mathslbb{X}",
        u"\uD584": "\\mathslbb{Y}",
        u"\uD585": "\\mathslbb{Z}",
        u"\uD586": "\\mathslbb{a}",
        u"\uD587": "\\mathslbb{b}",
        u"\uD588": "\\mathslbb{c}",
        u"\uD589": "\\mathslbb{d}",
        u"\uD58A": "\\mathslbb{e}",
        u"\uD58B": "\\mathslbb{f}",
        u"\uD58C": "\\mathslbb{g}",
        u"\uD58D": "\\mathslbb{h}",
        u"\uD58E": "\\mathslbb{i}",
        u"\uD58F": "\\mathslbb{j}",
        u"\uD590": "\\mathslbb{k}",
        u"\uD591": "\\mathslbb{l}",
        u"\uD592": "\\mathslbb{m}",
        u"\uD593": "\\mathslbb{n}",
        u"\uD594": "\\mathslbb{o}",
        u"\uD595": "\\mathslbb{p}",
        u"\uD596": "\\mathslbb{q}",
        u"\uD597": "\\mathslbb{r}",
        u"\uD598": "\\mathslbb{s}",
        u"\uD599": "\\mathslbb{t}",
        u"\uD59A": "\\mathslbb{u}",
        u"\uD59B": "\\mathslbb{v}",
        u"\uD59C": "\\mathslbb{w}",
        u"\uD59D": "\\mathslbb{x}",
        u"\uD59E": "\\mathslbb{y}",
        u"\uD59F": "\\mathslbb{z}",
        u"\uD5A0": "\\mathsf{A}",
        u"\uD5A1": "\\mathsf{B}",
        u"\uD5A2": "\\mathsf{C}",
        u"\uD5A3": "\\mathsf{D}",
        u"\uD5A4": "\\mathsf{E}",
        u"\uD5A5": "\\mathsf{F}",
        u"\uD5A6": "\\mathsf{G}",
        u"\uD5A7": "\\mathsf{H}",
        u"\uD5A8": "\\mathsf{I}",
        u"\uD5A9": "\\mathsf{J}",
        u"\uD5AA": "\\mathsf{K}",
        u"\uD5AB": "\\mathsf{L}",
        u"\uD5AC": "\\mathsf{M}",
        u"\uD5AD": "\\mathsf{N}",
        u"\uD5AE": "\\mathsf{O}",
        u"\uD5AF": "\\mathsf{P}",
        u"\uD5B0": "\\mathsf{Q}",
        u"\uD5B1": "\\mathsf{R}",
        u"\uD5B2": "\\mathsf{S}",
        u"\uD5B3": "\\mathsf{T}",
        u"\uD5B4": "\\mathsf{U}",
        u"\uD5B5": "\\mathsf{V}",
        u"\uD5B6": "\\mathsf{W}",
        u"\uD5B7": "\\mathsf{X}",
        u"\uD5B8": "\\mathsf{Y}",
        u"\uD5B9": "\\mathsf{Z}",
        u"\uD5BA": "\\mathsf{a}",
        u"\uD5BB": "\\mathsf{b}",
        u"\uD5BC": "\\mathsf{c}",
        u"\uD5BD": "\\mathsf{d}",
        u"\uD5BE": "\\mathsf{e}",
        u"\uD5BF": "\\mathsf{f}",
        u"\uD5C0": "\\mathsf{g}",
        u"\uD5C1": "\\mathsf{h}",
        u"\uD5C2": "\\mathsf{i}",
        u"\uD5C3": "\\mathsf{j}",
        u"\uD5C4": "\\mathsf{k}",
        u"\uD5C5": "\\mathsf{l}",
        u"\uD5C6": "\\mathsf{m}",
        u"\uD5C7": "\\mathsf{n}",
        u"\uD5C8": "\\mathsf{o}",
        u"\uD5C9": "\\mathsf{p}",
        u"\uD5CA": "\\mathsf{q}",
        u"\uD5CB": "\\mathsf{r}",
        u"\uD5CC": "\\mathsf{s}",
        u"\uD5CD": "\\mathsf{t}",
        u"\uD5CE": "\\mathsf{u}",
        u"\uD5CF": "\\mathsf{v}",
        u"\uD5D0": "\\mathsf{w}",
        u"\uD5D1": "\\mathsf{x}",
        u"\uD5D2": "\\mathsf{y}",
        u"\uD5D3": "\\mathsf{z}",
        u"\uD5D4": "\\mathsfbf{A}",
        u"\uD5D5": "\\mathsfbf{B}",
        u"\uD5D6": "\\mathsfbf{C}",
        u"\uD5D7": "\\mathsfbf{D}",
        u"\uD5D8": "\\mathsfbf{E}",
        u"\uD5D9": "\\mathsfbf{F}",
        u"\uD5DA": "\\mathsfbf{G}",
        u"\uD5DB": "\\mathsfbf{H}",
        u"\uD5DC": "\\mathsfbf{I}",
        u"\uD5DD": "\\mathsfbf{J}",
        u"\uD5DE": "\\mathsfbf{K}",
        u"\uD5DF": "\\mathsfbf{L}",
        u"\uD5E0": "\\mathsfbf{M}",
        u"\uD5E1": "\\mathsfbf{N}",
        u"\uD5E2": "\\mathsfbf{O}",
        u"\uD5E3": "\\mathsfbf{P}",
        u"\uD5E4": "\\mathsfbf{Q}",
        u"\uD5E5": "\\mathsfbf{R}",
        u"\uD5E6": "\\mathsfbf{S}",
        u"\uD5E7": "\\mathsfbf{T}",
        u"\uD5E8": "\\mathsfbf{U}",
        u"\uD5E9": "\\mathsfbf{V}",
        u"\uD5EA": "\\mathsfbf{W}",
        u"\uD5EB": "\\mathsfbf{X}",
        u"\uD5EC": "\\mathsfbf{Y}",
        u"\uD5ED": "\\mathsfbf{Z}",
        u"\uD5EE": "\\mathsfbf{a}",
        u"\uD5EF": "\\mathsfbf{b}",
        u"\uD5F0": "\\mathsfbf{c}",
        u"\uD5F1": "\\mathsfbf{d}",
        u"\uD5F2": "\\mathsfbf{e}",
        u"\uD5F3": "\\mathsfbf{f}",
        u"\uD5F4": "\\mathsfbf{g}",
        u"\uD5F5": "\\mathsfbf{h}",
        u"\uD5F6": "\\mathsfbf{i}",
        u"\uD5F7": "\\mathsfbf{j}",
        u"\uD5F8": "\\mathsfbf{k}",
        u"\uD5F9": "\\mathsfbf{l}",
        u"\uD5FA": "\\mathsfbf{m}",
        u"\uD5FB": "\\mathsfbf{n}",
        u"\uD5FC": "\\mathsfbf{o}",
        u"\uD5FD": "\\mathsfbf{p}",
        u"\uD5FE": "\\mathsfbf{q}",
        u"\uD5FF": "\\mathsfbf{r}",
        u"\uD600": "\\mathsfbf{s}",
        u"\uD601": "\\mathsfbf{t}",
        u"\uD602": "\\mathsfbf{u}",
        u"\uD603": "\\mathsfbf{v}",
        u"\uD604": "\\mathsfbf{w}",
        u"\uD605": "\\mathsfbf{x}",
        u"\uD606": "\\mathsfbf{y}",
        u"\uD607": "\\mathsfbf{z}",
        u"\uD608": "\\mathsfsl{A}",
        u"\uD609": "\\mathsfsl{B}",
        u"\uD60A": "\\mathsfsl{C}",
        u"\uD60B": "\\mathsfsl{D}",
        u"\uD60C": "\\mathsfsl{E}",
        u"\uD60D": "\\mathsfsl{F}",
        u"\uD60E": "\\mathsfsl{G}",
        u"\uD60F": "\\mathsfsl{H}",
        u"\uD610": "\\mathsfsl{I}",
        u"\uD611": "\\mathsfsl{J}",
        u"\uD612": "\\mathsfsl{K}",
        u"\uD613": "\\mathsfsl{L}",
        u"\uD614": "\\mathsfsl{M}",
        u"\uD615": "\\mathsfsl{N}",
        u"\uD616": "\\mathsfsl{O}",
        u"\uD617": "\\mathsfsl{P}",
        u"\uD618": "\\mathsfsl{Q}",
        u"\uD619": "\\mathsfsl{R}",
        u"\uD61A": "\\mathsfsl{S}",
        u"\uD61B": "\\mathsfsl{T}",
        u"\uD61C": "\\mathsfsl{U}",
        u"\uD61D": "\\mathsfsl{V}",
        u"\uD61E": "\\mathsfsl{W}",
        u"\uD61F": "\\mathsfsl{X}",
        u"\uD620": "\\mathsfsl{Y}",
        u"\uD621": "\\mathsfsl{Z}",
        u"\uD622": "\\mathsfsl{a}",
        u"\uD623": "\\mathsfsl{b}",
        u"\uD624": "\\mathsfsl{c}",
        u"\uD625": "\\mathsfsl{d}",
        u"\uD626": "\\mathsfsl{e}",
        u"\uD627": "\\mathsfsl{f}",
        u"\uD628": "\\mathsfsl{g}",
        u"\uD629": "\\mathsfsl{h}",
        u"\uD62A": "\\mathsfsl{i}",
        u"\uD62B": "\\mathsfsl{j}",
        u"\uD62C": "\\mathsfsl{k}",
        u"\uD62D": "\\mathsfsl{l}",
        u"\uD62E": "\\mathsfsl{m}",
        u"\uD62F": "\\mathsfsl{n}",
        u"\uD630": "\\mathsfsl{o}",
        u"\uD631": "\\mathsfsl{p}",
        u"\uD632": "\\mathsfsl{q}",
        u"\uD633": "\\mathsfsl{r}",
        u"\uD634": "\\mathsfsl{s}",
        u"\uD635": "\\mathsfsl{t}",
        u"\uD636": "\\mathsfsl{u}",
        u"\uD637": "\\mathsfsl{v}",
        u"\uD638": "\\mathsfsl{w}",
        u"\uD639": "\\mathsfsl{x}",
        u"\uD63A": "\\mathsfsl{y}",
        u"\uD63B": "\\mathsfsl{z}",
        u"\uD63C": "\\mathsfbfsl{A}",
        u"\uD63D": "\\mathsfbfsl{B}",
        u"\uD63E": "\\mathsfbfsl{C}",
        u"\uD63F": "\\mathsfbfsl{D}",
        u"\uD640": "\\mathsfbfsl{E}",
        u"\uD641": "\\mathsfbfsl{F}",
        u"\uD642": "\\mathsfbfsl{G}",
        u"\uD643": "\\mathsfbfsl{H}",
        u"\uD644": "\\mathsfbfsl{I}",
        u"\uD645": "\\mathsfbfsl{J}",
        u"\uD646": "\\mathsfbfsl{K}",
        u"\uD647": "\\mathsfbfsl{L}",
        u"\uD648": "\\mathsfbfsl{M}",
        u"\uD649": "\\mathsfbfsl{N}",
        u"\uD64A": "\\mathsfbfsl{O}",
        u"\uD64B": "\\mathsfbfsl{P}",
        u"\uD64C": "\\mathsfbfsl{Q}",
        u"\uD64D": "\\mathsfbfsl{R}",
        u"\uD64E": "\\mathsfbfsl{S}",
        u"\uD64F": "\\mathsfbfsl{T}",
        u"\uD650": "\\mathsfbfsl{U}",
        u"\uD651": "\\mathsfbfsl{V}",
        u"\uD652": "\\mathsfbfsl{W}",
        u"\uD653": "\\mathsfbfsl{X}",
        u"\uD654": "\\mathsfbfsl{Y}",
        u"\uD655": "\\mathsfbfsl{Z}",
        u"\uD656": "\\mathsfbfsl{a}",
        u"\uD657": "\\mathsfbfsl{b}",
        u"\uD658": "\\mathsfbfsl{c}",
        u"\uD659": "\\mathsfbfsl{d}",
        u"\uD65A": "\\mathsfbfsl{e}",
        u"\uD65B": "\\mathsfbfsl{f}",
        u"\uD65C": "\\mathsfbfsl{g}",
        u"\uD65D": "\\mathsfbfsl{h}",
        u"\uD65E": "\\mathsfbfsl{i}",
        u"\uD65F": "\\mathsfbfsl{j}",
        u"\uD660": "\\mathsfbfsl{k}",
        u"\uD661": "\\mathsfbfsl{l}",
        u"\uD662": "\\mathsfbfsl{m}",
        u"\uD663": "\\mathsfbfsl{n}",
        u"\uD664": "\\mathsfbfsl{o}",
        u"\uD665": "\\mathsfbfsl{p}",
        u"\uD666": "\\mathsfbfsl{q}",
        u"\uD667": "\\mathsfbfsl{r}",
        u"\uD668": "\\mathsfbfsl{s}",
        u"\uD669": "\\mathsfbfsl{t}",
        u"\uD66A": "\\mathsfbfsl{u}",
        u"\uD66B": "\\mathsfbfsl{v}",
        u"\uD66C": "\\mathsfbfsl{w}",
        u"\uD66D": "\\mathsfbfsl{x}",
        u"\uD66E": "\\mathsfbfsl{y}",
        u"\uD66F": "\\mathsfbfsl{z}",
        u"\uD670": "\\mathtt{A}",
        u"\uD671": "\\mathtt{B}",
        u"\uD672": "\\mathtt{C}",
        u"\uD673": "\\mathtt{D}",
        u"\uD674": "\\mathtt{E}",
        u"\uD675": "\\mathtt{F}",
        u"\uD676": "\\mathtt{G}",
        u"\uD677": "\\mathtt{H}",
        u"\uD678": "\\mathtt{I}",
        u"\uD679": "\\mathtt{J}",
        u"\uD67A": "\\mathtt{K}",
        u"\uD67B": "\\mathtt{L}",
        u"\uD67C": "\\mathtt{M}",
        u"\uD67D": "\\mathtt{N}",
        u"\uD67E": "\\mathtt{O}",
        u"\uD67F": "\\mathtt{P}",
        u"\uD680": "\\mathtt{Q}",
        u"\uD681": "\\mathtt{R}",
        u"\uD682": "\\mathtt{S}",
        u"\uD683": "\\mathtt{T}",
        u"\uD684": "\\mathtt{U}",
        u"\uD685": "\\mathtt{V}",
        u"\uD686": "\\mathtt{W}",
        u"\uD687": "\\mathtt{X}",
        u"\uD688": "\\mathtt{Y}",
        u"\uD689": "\\mathtt{Z}",
        u"\uD68A": "\\mathtt{a}",
        u"\uD68B": "\\mathtt{b}",
        u"\uD68C": "\\mathtt{c}",
        u"\uD68D": "\\mathtt{d}",
        u"\uD68E": "\\mathtt{e}",
        u"\uD68F": "\\mathtt{f}",
        u"\uD690": "\\mathtt{g}",
        u"\uD691": "\\mathtt{h}",
        u"\uD692": "\\mathtt{i}",
        u"\uD693": "\\mathtt{j}",
        u"\uD694": "\\mathtt{k}",
        u"\uD695": "\\mathtt{l}",
        u"\uD696": "\\mathtt{m}",
        u"\uD697": "\\mathtt{n}",
        u"\uD698": "\\mathtt{o}",
        u"\uD699": "\\mathtt{p}",
        u"\uD69A": "\\mathtt{q}",
        u"\uD69B": "\\mathtt{r}",
        u"\uD69C": "\\mathtt{s}",
        u"\uD69D": "\\mathtt{t}",
        u"\uD69E": "\\mathtt{u}",
        u"\uD69F": "\\mathtt{v}",
        u"\uD6A0": "\\mathtt{w}",
        u"\uD6A1": "\\mathtt{x}",
        u"\uD6A2": "\\mathtt{y}",
        u"\uD6A3": "\\mathtt{z}",
        u"\uD6A8": "\\mathbf{\\Alpha}",
        u"\uD6A9": "\\mathbf{\\Beta}",
        u"\uD6AA": "\\mathbf{\\Gamma}",
        u"\uD6AB": "\\mathbf{\\Delta}",
        u"\uD6AC": "\\mathbf{\\Epsilon}",
        u"\uD6AD": "\\mathbf{\\Zeta}",
        u"\uD6AE": "\\mathbf{\\Eta}",
        u"\uD6AF": "\\mathbf{\\Theta}",
        u"\uD6B0": "\\mathbf{\\Iota}",
        u"\uD6B1": "\\mathbf{\\Kappa}",
        u"\uD6B2": "\\mathbf{\\Lambda}",
        u"\uD6B5": "\\mathbf{\\Xi}",
        u"\uD6B7": "\\mathbf{\\Pi}",
        u"\uD6B8": "\\mathbf{\\Rho}",
        u"\uD6B9": "\\mathbf{\\vartheta}",
        u"\uD6BA": "\\mathbf{\\Sigma}",
        u"\uD6BB": "\\mathbf{\\Tau}",
        u"\uD6BC": "\\mathbf{\\Upsilon}",
        u"\uD6BD": "\\mathbf{\\Phi}",
        u"\uD6BE": "\\mathbf{\\Chi}",
        u"\uD6BF": "\\mathbf{\\Psi}",
        u"\uD6C0": "\\mathbf{\\Omega}",
        u"\uD6C1": "\\mathbf{\\nabla}",
        u"\uD6C2": "\\mathbf{\\Alpha}",
        u"\uD6C3": "\\mathbf{\\Beta}",
        u"\uD6C4": "\\mathbf{\\Gamma}",
        u"\uD6C5": "\\mathbf{\\Delta}",
        u"\uD6C6": "\\mathbf{\\Epsilon}",
        u"\uD6C7": "\\mathbf{\\Zeta}",
        u"\uD6C8": "\\mathbf{\\Eta}",
        u"\uD6C9": "\\mathbf{\\theta}",
        u"\uD6CA": "\\mathbf{\\Iota}",
        u"\uD6CB": "\\mathbf{\\Kappa}",
        u"\uD6CC": "\\mathbf{\\Lambda}",
        u"\uD6CF": "\\mathbf{\\Xi}",
        u"\uD6D1": "\\mathbf{\\Pi}",
        u"\uD6D2": "\\mathbf{\\Rho}",
        u"\uD6D3": "\\mathbf{\\varsigma}",
        u"\uD6D4": "\\mathbf{\\Sigma}",
        u"\uD6D5": "\\mathbf{\\Tau}",
        u"\uD6D6": "\\mathbf{\\Upsilon}",
        u"\uD6D7": "\\mathbf{\\Phi}",
        u"\uD6D8": "\\mathbf{\\Chi}",
        u"\uD6D9": "\\mathbf{\\Psi}",
        u"\uD6DA": "\\mathbf{\\Omega}",
        u"\uD6DB": "\\partial ",
        u"\uD6DC": "\\in",
        u"\uD6DD": "\\mathbf{\\vartheta}",
        u"\uD6DE": "\\mathbf{\\varkappa}",
        u"\uD6DF": "\\mathbf{\\phi}",
        u"\uD6E0": "\\mathbf{\\varrho}",
        u"\uD6E1": "\\mathbf{\\varpi}",
        u"\uD6E2": "\\mathsl{\\Alpha}",
        u"\uD6E3": "\\mathsl{\\Beta}",
        u"\uD6E4": "\\mathsl{\\Gamma}",
        u"\uD6E5": "\\mathsl{\\Delta}",
        u"\uD6E6": "\\mathsl{\\Epsilon}",
        u"\uD6E7": "\\mathsl{\\Zeta}",
        u"\uD6E8": "\\mathsl{\\Eta}",
        u"\uD6E9": "\\mathsl{\\Theta}",
        u"\uD6EA": "\\mathsl{\\Iota}",
        u"\uD6EB": "\\mathsl{\\Kappa}",
        u"\uD6EC": "\\mathsl{\\Lambda}",
        u"\uD6EF": "\\mathsl{\\Xi}",
        u"\uD6F1": "\\mathsl{\\Pi}",
        u"\uD6F2": "\\mathsl{\\Rho}",
        u"\uD6F3": "\\mathsl{\\vartheta}",
        u"\uD6F4": "\\mathsl{\\Sigma}",
        u"\uD6F5": "\\mathsl{\\Tau}",
        u"\uD6F6": "\\mathsl{\\Upsilon}",
        u"\uD6F7": "\\mathsl{\\Phi}",
        u"\uD6F8": "\\mathsl{\\Chi}",
        u"\uD6F9": "\\mathsl{\\Psi}",
        u"\uD6FA": "\\mathsl{\\Omega}",
        u"\uD6FB": "\\mathsl{\\nabla}",
        u"\uD6FC": "\\mathsl{\\Alpha}",
        u"\uD6FD": "\\mathsl{\\Beta}",
        u"\uD6FE": "\\mathsl{\\Gamma}",
        u"\uD6FF": "\\mathsl{\\Delta}",
        u"\uD700": "\\mathsl{\\Epsilon}",
        u"\uD701": "\\mathsl{\\Zeta}",
        u"\uD702": "\\mathsl{\\Eta}",
        u"\uD703": "\\mathsl{\\Theta}",
        u"\uD704": "\\mathsl{\\Iota}",
        u"\uD705": "\\mathsl{\\Kappa}",
        u"\uD706": "\\mathsl{\\Lambda}",
        u"\uD709": "\\mathsl{\\Xi}",
        u"\uD70B": "\\mathsl{\\Pi}",
        u"\uD70C": "\\mathsl{\\Rho}",
        u"\uD70D": "\\mathsl{\\varsigma}",
        u"\uD70E": "\\mathsl{\\Sigma}",
        u"\uD70F": "\\mathsl{\\Tau}",
        u"\uD710": "\\mathsl{\\Upsilon}",
        u"\uD711": "\\mathsl{\\Phi}",
        u"\uD712": "\\mathsl{\\Chi}",
        u"\uD713": "\\mathsl{\\Psi}",
        u"\uD714": "\\mathsl{\\Omega}",
        u"\uD715": "\\partial ",
        u"\uD716": "\\in",
        u"\uD717": "\\mathsl{\\vartheta}",
        u"\uD718": "\\mathsl{\\varkappa}",
        u"\uD719": "\\mathsl{\\phi}",
        u"\uD71A": "\\mathsl{\\varrho}",
        u"\uD71B": "\\mathsl{\\varpi}",
        u"\uD71C": "\\mathbit{\\Alpha}",
        u"\uD71D": "\\mathbit{\\Beta}",
        u"\uD71E": "\\mathbit{\\Gamma}",
        u"\uD71F": "\\mathbit{\\Delta}",
        u"\uD720": "\\mathbit{\\Epsilon}",
        u"\uD721": "\\mathbit{\\Zeta}",
        u"\uD722": "\\mathbit{\\Eta}",
        u"\uD723": "\\mathbit{\\Theta}",
        u"\uD724": "\\mathbit{\\Iota}",
        u"\uD725": "\\mathbit{\\Kappa}",
        u"\uD726": "\\mathbit{\\Lambda}",
        u"\uD729": "\\mathbit{\\Xi}",
        u"\uD72B": "\\mathbit{\\Pi}",
        u"\uD72C": "\\mathbit{\\Rho}",
        u"\uD72D": "\\mathbit{O}",
        u"\uD72E": "\\mathbit{\\Sigma}",
        u"\uD72F": "\\mathbit{\\Tau}",
        u"\uD730": "\\mathbit{\\Upsilon}",
        u"\uD731": "\\mathbit{\\Phi}",
        u"\uD732": "\\mathbit{\\Chi}",
        u"\uD733": "\\mathbit{\\Psi}",
        u"\uD734": "\\mathbit{\\Omega}",
        u"\uD735": "\\mathbit{\\nabla}",
        u"\uD736": "\\mathbit{\\Alpha}",
        u"\uD737": "\\mathbit{\\Beta}",
        u"\uD738": "\\mathbit{\\Gamma}",
        u"\uD739": "\\mathbit{\\Delta}",
        u"\uD73A": "\\mathbit{\\Epsilon}",
        u"\uD73B": "\\mathbit{\\Zeta}",
        u"\uD73C": "\\mathbit{\\Eta}",
        u"\uD73D": "\\mathbit{\\Theta}",
        u"\uD73E": "\\mathbit{\\Iota}",
        u"\uD73F": "\\mathbit{\\Kappa}",
        u"\uD740": "\\mathbit{\\Lambda}",
        u"\uD743": "\\mathbit{\\Xi}",
        u"\uD745": "\\mathbit{\\Pi}",
        u"\uD746": "\\mathbit{\\Rho}",
        u"\uD747": "\\mathbit{\\varsigma}",
        u"\uD748": "\\mathbit{\\Sigma}",
        u"\uD749": "\\mathbit{\\Tau}",
        u"\uD74A": "\\mathbit{\\Upsilon}",
        u"\uD74B": "\\mathbit{\\Phi}",
        u"\uD74C": "\\mathbit{\\Chi}",
        u"\uD74D": "\\mathbit{\\Psi}",
        u"\uD74E": "\\mathbit{\\Omega}",
        u"\uD74F": "\\partial ",
        u"\uD750": "\\in",
        u"\uD751": "\\mathbit{\\vartheta}",
        u"\uD752": "\\mathbit{\\varkappa}",
        u"\uD753": "\\mathbit{\\phi}",
        u"\uD754": "\\mathbit{\\varrho}",
        u"\uD755": "\\mathbit{\\varpi}",
        u"\uD756": "\\mathsfbf{\\Alpha}",
        u"\uD757": "\\mathsfbf{\\Beta}",
        u"\uD758": "\\mathsfbf{\\Gamma}",
        u"\uD759": "\\mathsfbf{\\Delta}",
        u"\uD75A": "\\mathsfbf{\\Epsilon}",
        u"\uD75B": "\\mathsfbf{\\Zeta}",
        u"\uD75C": "\\mathsfbf{\\Eta}",
        u"\uD75D": "\\mathsfbf{\\Theta}",
        u"\uD75E": "\\mathsfbf{\\Iota}",
        u"\uD75F": "\\mathsfbf{\\Kappa}",
        u"\uD760": "\\mathsfbf{\\Lambda}",
        u"\uD763": "\\mathsfbf{\\Xi}",
        u"\uD765": "\\mathsfbf{\\Pi}",
        u"\uD766": "\\mathsfbf{\\Rho}",
        u"\uD767": "\\mathsfbf{\\vartheta}",
        u"\uD768": "\\mathsfbf{\\Sigma}",
        u"\uD769": "\\mathsfbf{\\Tau}",
        u"\uD76A": "\\mathsfbf{\\Upsilon}",
        u"\uD76B": "\\mathsfbf{\\Phi}",
        u"\uD76C": "\\mathsfbf{\\Chi}",
        u"\uD76D": "\\mathsfbf{\\Psi}",
        u"\uD76E": "\\mathsfbf{\\Omega}",
        u"\uD76F": "\\mathsfbf{\\nabla}",
        u"\uD770": "\\mathsfbf{\\Alpha}",
        u"\uD771": "\\mathsfbf{\\Beta}",
        u"\uD772": "\\mathsfbf{\\Gamma}",
        u"\uD773": "\\mathsfbf{\\Delta}",
        u"\uD774": "\\mathsfbf{\\Epsilon}",
        u"\uD775": "\\mathsfbf{\\Zeta}",
        u"\uD776": "\\mathsfbf{\\Eta}",
        u"\uD777": "\\mathsfbf{\\Theta}",
        u"\uD778": "\\mathsfbf{\\Iota}",
        u"\uD779": "\\mathsfbf{\\Kappa}",
        u"\uD77A": "\\mathsfbf{\\Lambda}",
        u"\uD77D": "\\mathsfbf{\\Xi}",
        u"\uD77F": "\\mathsfbf{\\Pi}",
        u"\uD780": "\\mathsfbf{\\Rho}",
        u"\uD781": "\\mathsfbf{\\varsigma}",
        u"\uD782": "\\mathsfbf{\\Sigma}",
        u"\uD783": "\\mathsfbf{\\Tau}",
        u"\uD784": "\\mathsfbf{\\Upsilon}",
        u"\uD785": "\\mathsfbf{\\Phi}",
        u"\uD786": "\\mathsfbf{\\Chi}",
        u"\uD787": "\\mathsfbf{\\Psi}",
        u"\uD788": "\\mathsfbf{\\Omega}",
        u"\uD789": "\\partial ",
        u"\uD78A": "\\in",
        u"\uD78B": "\\mathsfbf{\\vartheta}",
        u"\uD78C": "\\mathsfbf{\\varkappa}",
        u"\uD78D": "\\mathsfbf{\\phi}",
        u"\uD78E": "\\mathsfbf{\\varrho}",
        u"\uD78F": "\\mathsfbf{\\varpi}",
        u"\uD790": "\\mathsfbfsl{\\Alpha}",
        u"\uD791": "\\mathsfbfsl{\\Beta}",
        u"\uD792": "\\mathsfbfsl{\\Gamma}",
        u"\uD793": "\\mathsfbfsl{\\Delta}",
        u"\uD794": "\\mathsfbfsl{\\Epsilon}",
        u"\uD795": "\\mathsfbfsl{\\Zeta}",
        u"\uD796": "\\mathsfbfsl{\\Eta}",
        u"\uD797": "\\mathsfbfsl{\\vartheta}",
        u"\uD798": "\\mathsfbfsl{\\Iota}",
        u"\uD799": "\\mathsfbfsl{\\Kappa}",
        u"\uD79A": "\\mathsfbfsl{\\Lambda}",
        u"\uD79D": "\\mathsfbfsl{\\Xi}",
        u"\uD79F": "\\mathsfbfsl{\\Pi}",
        u"\uD7A0": "\\mathsfbfsl{\\Rho}",
        u"\uD7A1": "\\mathsfbfsl{\\vartheta}",
        u"\uD7A2": "\\mathsfbfsl{\\Sigma}",
        u"\uD7A3": "\\mathsfbfsl{\\Tau}",
        u"\uD7A4": "\\mathsfbfsl{\\Upsilon}",
        u"\uD7A5": "\\mathsfbfsl{\\Phi}",
        u"\uD7A6": "\\mathsfbfsl{\\Chi}",
        u"\uD7A7": "\\mathsfbfsl{\\Psi}",
        u"\uD7A8": "\\mathsfbfsl{\\Omega}",
        u"\uD7A9": "\\mathsfbfsl{\\nabla}",
        u"\uD7AA": "\\mathsfbfsl{\\Alpha}",
        u"\uD7AB": "\\mathsfbfsl{\\Beta}",
        u"\uD7AC": "\\mathsfbfsl{\\Gamma}",
        u"\uD7AD": "\\mathsfbfsl{\\Delta}",
        u"\uD7AE": "\\mathsfbfsl{\\Epsilon}",
        u"\uD7AF": "\\mathsfbfsl{\\Zeta}",
        u"\uD7B0": "\\mathsfbfsl{\\Eta}",
        u"\uD7B1": "\\mathsfbfsl{\\vartheta}",
        u"\uD7B2": "\\mathsfbfsl{\\Iota}",
        u"\uD7B3": "\\mathsfbfsl{\\Kappa}",
        u"\uD7B4": "\\mathsfbfsl{\\Lambda}",
        u"\uD7B7": "\\mathsfbfsl{\\Xi}",
        u"\uD7B9": "\\mathsfbfsl{\\Pi}",
        u"\uD7BA": "\\mathsfbfsl{\\Rho}",
        u"\uD7BB": "\\mathsfbfsl{\\varsigma}",
        u"\uD7BC": "\\mathsfbfsl{\\Sigma}",
        u"\uD7BD": "\\mathsfbfsl{\\Tau}",
        u"\uD7BE": "\\mathsfbfsl{\\Upsilon}",
        u"\uD7BF": "\\mathsfbfsl{\\Phi}",
        u"\uD7C0": "\\mathsfbfsl{\\Chi}",
        u"\uD7C1": "\\mathsfbfsl{\\Psi}",
        u"\uD7C2": "\\mathsfbfsl{\\Omega}",
        u"\uD7C3": "\\partial ",
        u"\uD7C4": "\\in",
        u"\uD7C5": "\\mathsfbfsl{\\vartheta}",
        u"\uD7C6": "\\mathsfbfsl{\\varkappa}",
        u"\uD7C7": "\\mathsfbfsl{\\phi}",
        u"\uD7C8": "\\mathsfbfsl{\\varrho}",
        u"\uD7C9": "\\mathsfbfsl{\\varpi}",
        u"\uD7CE": "\\mathbf{0}",
        u"\uD7CF": "\\mathbf{1}",
        u"\uD7D0": "\\mathbf{2}",
        u"\uD7D1": "\\mathbf{3}",
        u"\uD7D2": "\\mathbf{4}",
        u"\uD7D3": "\\mathbf{5}",
        u"\uD7D4": "\\mathbf{6}",
        u"\uD7D5": "\\mathbf{7}",
        u"\uD7D6": "\\mathbf{8}",
        u"\uD7D7": "\\mathbf{9}",
        u"\uD7D8": "\\mathbb{0}",
        u"\uD7D9": "\\mathbb{1}",
        u"\uD7DA": "\\mathbb{2}",
        u"\uD7DB": "\\mathbb{3}",
        u"\uD7DC": "\\mathbb{4}",
        u"\uD7DD": "\\mathbb{5}",
        u"\uD7DE": "\\mathbb{6}",
        u"\uD7DF": "\\mathbb{7}",
        u"\uD7E0": "\\mathbb{8}",
        u"\uD7E1": "\\mathbb{9}",
        u"\uD7E2": "\\mathsf{0}",
        u"\uD7E3": "\\mathsf{1}",
        u"\uD7E4": "\\mathsf{2}",
        u"\uD7E5": "\\mathsf{3}",
        u"\uD7E6": "\\mathsf{4}",
        u"\uD7E7": "\\mathsf{5}",
        u"\uD7E8": "\\mathsf{6}",
        u"\uD7E9": "\\mathsf{7}",
        u"\uD7EA": "\\mathsf{8}",
        u"\uD7EB": "\\mathsf{9}",
        u"\uD7EC": "\\mathsfbf{0}",
        u"\uD7ED": "\\mathsfbf{1}",
        u"\uD7EE": "\\mathsfbf{2}",
        u"\uD7EF": "\\mathsfbf{3}",
        u"\uD7F0": "\\mathsfbf{4}",
        u"\uD7F1": "\\mathsfbf{5}",
        u"\uD7F2": "\\mathsfbf{6}",
        u"\uD7F3": "\\mathsfbf{7}",
        u"\uD7F4": "\\mathsfbf{8}",
        u"\uD7F5": "\\mathsfbf{9}",
        u"\uD7F6": "\\mathtt{0}",
        u"\uD7F7": "\\mathtt{1}",
        u"\uD7F8": "\\mathtt{2}",
        u"\uD7F9": "\\mathtt{3}",
        u"\uD7FA": "\\mathtt{4}",
        u"\uD7FB": "\\mathtt{5}",
        u"\uD7FC": "\\mathtt{6}",
        u"\uD7FD": "\\mathtt{7}",
        u"\uD7FE": "\\mathtt{8}",
        u"\uD7FF": "\\mathtt{9}",
    }

def parse(filehandle=sys.stdin):
    parser = BibTexParser(filehandle)
    records, metadata = parser.parse()
    if len(records) > 0:
        sys.stdout.write(json.dumps({'records':records, 'metadata':metadata}))
    else:
        sys.stderr.write('Zero records were parsed from the data')
    
def main():
    conf = {"display_name": "BibTex",
            "format": "bibtex",
            "contact": "openbiblio-dev@lists.okfn.org", 
            "bibserver_plugin": True, 
            "BibJSON_version": "0.81"}        
    for x in sys.argv[1:]:
        if x == '-bibserver':
            sys.stdout.write(json.dumps(conf))
            sys.exit()
        else:
            parse(open(x))
            sys.exit()
    parse()
            
if __name__ == '__main__':
    main()    

########NEW FILE########
__FILENAME__ = csvparser
#!/usr/bin/env python
import csv
import sys
import json
import chardet
import cStringIO

class CSVParser(object):

    def __init__(self, fileobj):

        data = fileobj.read()
        self.encoding = chardet.detect(data).get('encoding', 'ascii')

        # Some files have Byte-order marks inserted at the start
        if data[:3] == '\xef\xbb\xbf':
            data = data[3:]
        self.fileobj = cStringIO.StringIO(data)


    def parse(self):
        #dialect = csv.Sniffer().sniff(fileobj.read(1024))
        d = csv.DictReader(self.fileobj)
        data = []

        # do any required conversions
        for row in d:
            for k, v in row.items():
                del row[k]
                row[k.lower()] = v
            if "author" in row:
                row["author"] = [{"name":i} for i in row["author"].split(",")]
            if "editor" in row:
                row["editor"] = [{"name":i} for i in row["editor"].split(",")]
            if "journal" in row:
                row["journal"] = {"name":row["journal"]}
            data.append(row)
        return data, {}
        
def parse():
    parser = CSVParser(sys.stdin)
    records, metadata = parser.parse()
    if len(records) > 0:
        sys.stdout.write(json.dumps({'records':records, 'metadata':metadata}))
    else:
        sys.stderr.write('Zero records were parsed from the data')

def main():
    conf = {"display_name": "CSV",
            "format": "csv",
            "contact": "openbiblio-dev@lists.okfn.org", 
            "bibserver_plugin": True, 
            "BibJSON_version": "0.81"}        
    for x in sys.argv[1:]:
        if x == '-bibserver':
            sys.stdout.write(json.dumps(conf))
            sys.exit()
    parse()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = JSONParser
#!/usr/bin/env python

import chardet, cStringIO
import json
import sys

class JSONParser(object):

    def __init__(self, fileobj):

        data = fileobj.read()
        self.encoding = chardet.detect(data).get('encoding', 'ascii')

        # Some files have Byte-order marks inserted at the start
        if data[:3] == '\xef\xbb\xbf':
            data = data[3:]
        self.fileobj = cStringIO.StringIO(data)

    def parse(self):
        incoming = json.load(self.fileobj)

        if 'records' in incoming:
            # if the incoming is bibjson, get records and metadata
            data = self.customisations(incoming['records'])
            metadata = incoming.get('metadata',{})
        else:
            data = incoming
            metadata = {}
    
        return data, metadata

    def customisations(self,records):
        for record in records:
            # tidy any errant authors as strings
            if 'author' in record:
                if ' and ' in record['author']:
                    record['author'] = record['author'].split(' and ')
            # do any conversions to objects
            for index,item in enumerate(record.get('author', [])):
                if not isinstance(item,dict):
                    record['author'][index] = {"name":item}
            # copy an citekey to cid
            if 'citekey' in record:
                record['id'] = record['citekey']
            if 'cid' in record:
                record['id'] = record['cid']
            # copy keys to singular
            if 'links' in record:
                record['link'] = record['links']
                del record['links']
        return records

def parse():
    parser = JSONParser(sys.stdin)
    records, metadata = parser.parse()
    if len(records) > 0:
        sys.stdout.write(json.dumps({'records':records, 'metadata':metadata}))
    else:
        sys.stderr.write('Zero records were parsed from the data')

def main():
    conf = {"display_name": "JSON",
            "format": "json",
            "contact": "openbiblio-dev@lists.okfn.org", 
            "bibserver_plugin": True, 
            "BibJSON_version": "0.81"}        
    for x in sys.argv[1:]:
        if x == '-bibserver':
            sys.stdout.write(json.dumps(conf))
            sys.exit()
    parse()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = NLMXMLParser
from xml.etree.ElementTree import ElementTree
from bibserver.parsers import BaseParser

'''this file can be called as a module or called directly from the command line like so:

python NLMXMLParser.py /path/to/file.xml

Returns a list of record dicts
Or just parse a record directly like so:

python NLMXMLParser.py '<?xml version='1.0'?><art>...'

Returns a record dict
'''



class NLMXMLParser(BaseParser):

    def __init__(self, fileobj):
        super(NLMXMLParser, self).__init__(fileobj)

        # set which bibjson schema this parser parses to
        self.schema = "v0.82"
        self.has_metadata = False
        self.persons = []

        self.identifier_types = ["doi","isbn","issn"]


    def parse(self):
        '''given a fileobject, parse it for NLM XML records,
        and pass them to the record parser'''
        records = []

        et = ElementTree()
        et.parse(self.fileobj)

        records.append(self.parse_front_matter(et.find('front')))

        records.extend(self.parse_references(et.findall('back/ref-list/ref')))

        return records, {"schema": self.schema}


    def parse_front_matter(self, front):

        article_meta = front.find('article-meta')
        journal_meta = front.find('journal-meta')

        record = {
            'title': self.get_article_title(article_meta),
            'author': self.get_article_authors(article_meta),
            'year': article_meta.findtext('pub-date/year'),
            'volume': article_meta.findtext('volume'),
            'number': article_meta.findtext('issue'),
            'pages': self.get_page_numbers(article_meta),

            'journal': self.get_journal_name(journal_meta),
            'publisher': self.get_journal_publisher_name(journal_meta)
        }

        doi = front.findtext('article-meta/article-id[@pub-id-type="doi"]')
        record['identifiers'] = [
            {'id': doi, 'type': 'doi'}
        ]

        return record

    def parse_references(self, ref_list):
        records = []
        for ref in ref_list:
            records.append(self.parse_reference(ref))
        return records

    def parse_reference(self, reference):

        citation = reference.find('citation')

        if citation.attrib['citation-type'] == 'journal':
            record = self.parse_journal(citation)

        elif citation.attrib['citation-type'] == 'other':
            record = self.parse_other(citation)

        else:
            raise Exception('Unsupported citation type: ' + citation.attrib['citation-type'])

        record['id'] = reference.attrib['id']

        return record

    def parse_journal(self, citation):
        return self.filter_empty_fields({
                'title': self.get_journal_citation_title(citation),
                'author': self.get_citation_authors(citation),
                'year': citation.findtext('year'),
                'journal': citation.findtext('source'),
                'volume': citation.findtext('volume'),
                'pages': self.get_page_numbers(citation)
            })

    def parse_other(self, citation):
        return self.filter_empty_fields({
                'title': self.get_other_citation_title(citation),
                'booktitle': self.get_other_citation_booktitle(citation),
                'author': self.get_citation_authors(citation),
                'editor': self.get_citation_editors(citation),
                'year': citation.findtext('year'),
                'publisher': self.get_citation_publisher(citation),
                'volume': citation.findtext('volume'),
                'pages': self.get_page_numbers(citation)
            })


    def get_article_title(self, article_meta):
        return "".join(article_meta.find('title-group/article-title').itertext())

    def get_article_authors(self, article_meta):
        return self.get_names(article_meta.findall('contrib-group/contrib[@contrib-type="author"]/name'))

    def get_page_numbers(self, context):
        if context.find('fpage') is None:
            return context.findtext('elocation-id')
        elif context.find('lpage') is None:
            return context.findtext('fpage')
        else:
            return '%s--%s' % (context.findtext('fpage'), context.findtext('lpage'))

    def get_journal_citation_title(self, citation):
        if citation.find('article-title') is None:
            return None
        else:
            return "".join(citation.find('article-title').itertext())

    def get_other_citation_title(self, citation):
        if citation.find('article-title') is None:
            return self.get_citation_source(citation)
        else:
            return "".join(citation.find('article-title').itertext())

    def get_other_citation_booktitle(self, citation):
        if citation.find('article-title') is None:
            return None
        else:
            return self.get_citation_source(citation)

    def get_citation_source(self, citation):
        if citation.find('source') is None:
            return None
        else:
            return "".join(citation.find('source').itertext())

    def get_citation_publisher(self, context):
        if context.find('publisher-name') is None:
            return None
        elif context.find('publisher-loc') is None:
            return context.findtext('publisher-name')
        else:
            return context.findtext('publisher-name') + ', ' + context.findtext('publisher-loc')


    def get_citation_authors(self, citation):
        return self.get_names(citation.findall('person-group[@person-group-type="author"]/name'))

    def get_citation_editors(self, citation):
        return self.get_names(citation.findall('person-group[@person-group-type="editor"]/name'))

    def get_journal_name(self, journal_meta):
        return journal_meta.findtext('.//journal-title');

    def get_journal_publisher_name(self, journal_meta):
        return journal_meta.findtext('.//publisher-name');


    def get_names(self, names):
        return ['%s, %s' % (name.findtext('surname'), name.findtext('given-names')) for name in names]

    def filter_empty_fields(self, dict):
        record = {}
        for k, v in dict.iteritems():
            if not v is None:
                record[k] = v
        return record


# in case file is run directly
if __name__ == "__main__":
    import sys
    parser = NLMXMLParser(open(sys.argv[1]))
    print parser.parse()




########NEW FILE########
__FILENAME__ = RISParser
#!/usr/bin/env python

'''this file to be called from the command line, expects RIS input on stdin.
Returns a list of record dicts, and metadata on stdout

Details of the RIS format
http://en.wikipedia.org/wiki/RIS_%28file_format%29
'''

import chardet, cStringIO
import sys
import json

FIELD_MAP = {
    "DO": "doi", 
    "SP": "pages", 
    "M2": "start page", 
    "DB": "name of database", 
    "DA": "date", 
    "M1": "number", 
    "M3": "type", 
    "N1": "notes", 
    "ST": "short title", 
    "DP": "database provider", 
    "CN": "call number", 
    "IS": "number", 
    "LB": "label", 
    "TA": "translated author", 
    "TY": "type ", 
    "UR": "url", 
    "TT": "translated title", 
    "PY": "year", 
    "PB": "publisher", 
    "A3": "tertiary author", 
    "C8": "custom 8", 
    "A4": "subsidiary author", 
    "TI": "title", 
    "C3": "custom 3", 
    "C2": "pmcid", 
    "C1": "note", 
    "C7": "custom 7", 
    "C6": "nihmsid", 
    "C5": "custom 5", 
    "C4": "custom 4", 
    "AB": "note", 
    "AD": "institution", 
    "VL": "volume", 
    "CA": "caption", 
    "T2": "secondary title", 
    "T3": "tertiary title", 
    "AN": "accession number", 
    "L4": "figure", 
    "NV": "number of volumes", 
    "AU": "author", 
    "RP": "reprint edition", 
    "L1": "file attachments", 
    "ET": "epub date", 
    "A2": "author", 
    "RN": "note", 
    "LA": "language", 
    "CY": "place published", 
    "J2": "alternate title", 
    "RI": "reviewed item", 
    "KW": "keyword", 
    "SN": "issn", 
    "Y2": "access date", 
    "SE": "section", 
    "OP": "original publication",
    "JF": "journal",
}

VALUE_MAP = {
    'AU' : lambda v: [{u'name':vv.decode('utf8')} for vv in v]
}
DEFAULT_VALUE_FUNC = lambda v: u' '.join(vv.decode('utf8') for vv in v)

class RISParser(object):

    def __init__(self, fileobj):

        data = fileobj.read()
        self.encoding = chardet.detect(data).get('encoding', 'ascii')

        # Some files have Byte-order marks inserted at the start
        if data[:3] == '\xef\xbb\xbf':
            data = data[3:]
        self.fileobj = cStringIO.StringIO(data)
        self.data = []
        
    def add_chunk(self, chunk):
        if not chunk: return
        tmp = {}
        for k,v in chunk.items():
            tmp[FIELD_MAP.get(k, k)] =  VALUE_MAP.get(k, DEFAULT_VALUE_FUNC)(v)   
        self.data.append(tmp)
        
    def parse(self):
        data, chunk = [], {}
        last_field = None
        for line in self.fileobj:
            if line.startswith(' ') and last_field:
                chunk.setdefault(last_field, []).append(line.strip())
                continue
            line = line.strip()
            if not line: continue
            parts = line.split('  - ')
            if len(parts) < 2:
                continue
            field = parts[0]
            last_field = field
            if field == 'TY':
                self.add_chunk(chunk)
                chunk = {}
            value = '  - '.join(parts[1:])
            if value:
                chunk.setdefault(field, []).append(value)
        self.add_chunk(chunk)
        return self.data, {}

def parse():
    parser = RISParser(sys.stdin)
    records, metadata = parser.parse()
    if len(records) > 0:
        sys.stdout.write(json.dumps({'records':records, 'metadata':metadata}))
    else:
        sys.stderr.write('Zero records were parsed from the data')
    
def main():
    conf = {"display_name": "RIS",
            "format": "ris",
            "contact": "openbiblio-dev@lists.okfn.org", 
            "bibserver_plugin": True, 
            "BibJSON_version": "0.81"}        
    for x in sys.argv[1:]:
        if x == '-bibserver':
            sys.stdout.write(json.dumps(conf))
            sys.exit()
    parse()
            
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = wikipedia
#!/usr/bin/env python

'''
Wikipedia search to citations parser
Reads a query term on stdin
'''

import os, sys
import re
import json
import urllib, urllib2, httplib
import traceback

def repl(matchobj):
    return matchobj.group(0)

def wikitext_to_dict(txt):
    buf = []
    for c in re.findall('{{Citation |cite journal(.*?)}}', txt):
        if c.strip().startswith('needed'): continue
        c = re.sub('{{.*?|.*?|(.*?)}}', repl, c)
        tmp = {}
        for cc in c.split('|'):
            ccc = cc.strip().split('=')
            if len(ccc) == 2:
                tmp[ccc[0].strip()] = ccc[1].strip()
        if tmp:
            if 'author' in tmp:
                auth_string = tmp['author'].split(',')
                tmp['author'] = []
                for au in auth_string:
                    au = au.strip()
                    if au.startswith('and '):
                        au = au[4:]
                    tmp.setdefault('author', []).append({'name':au})
            name = '%s %s' % (tmp.get('first',''), tmp.get('last', ''))
            if name.strip():
                tmp.setdefault('author', []).append({'name':name})
            if 'journal' in tmp:
                tmp['journal'] = {'name':tmp['journal']}
            buf.append(tmp)
    return buf
    
def parse(local_cache):
    q = sys.stdin.read()
    URL = 'http://en.wikipedia.org/w/api.php?action=query&list=search&srlimit=50&srprop=wordcount&format=json&srsearch='
    URLraw = 'http://en.wikipedia.org/w/index.php?action=raw&title='
    data_json = False
    if local_cache:
        try:
            cached_data = json.loads(open('wikipedia.py.data').read())
            data_json = cached_data.get('data1', {})
        except IOError:
            cached_data = {'data1':{}, 'data2':{}}            
    if not data_json:
        data = urllib2.urlopen(URL+urllib.quote_plus(q)).read()
        data_json = json.loads(data)
    if local_cache:
        cached_data['data1'] = data_json
    records = []
    
    try:
        search_result = data_json.get("query")
        if not search_result: search_result = data_json.get("query-continue", {"search":[]})
        for x in search_result["search"]:
            if x['wordcount'] > 20:
                quoted_title = urllib.quote_plus(x['title'].encode('utf8'))
                try:
                    title_data = None
                    if local_cache:
                        title_data = cached_data.get('data2',{}).get(quoted_title)
                    if title_data is None:
                        title_data = urllib2.urlopen(URLraw+quoted_title).read()
                    if local_cache:
                        cached_data.setdefault('data2', {})[quoted_title] = title_data
                except httplib.BadStatusLine:
                    sys.stderr.write('Problem reading %s\n' % (URLraw+quoted_title))
                    continue
                citations = wikitext_to_dict(title_data)
                if citations:
                    for c in citations:
                        c['link'] = [{'url':'http://en.wikipedia.org/wiki/'+quoted_title}]
                    records.extend(citations)
    except:
        sys.stderr.write(traceback.format_exc())
    sys.stdout.write(json.dumps({'records':records, 'metadata':{}}))
    if local_cache:
        open('wikipedia.py.data', 'w').write(json.dumps(cached_data))
    
def main():
    conf = {"display_name": "Wikipedia search to citations",
            "format": "wikipedia",
            "downloads": True,
            "contact": "openbiblio-dev@lists.okfn.org", 
            "bibserver_plugin": True, 
            "BibJSON_version": "0.81"}
    local_cache = False        
    for x in sys.argv[1:]:
        if x == '-bibserver':
            sys.stdout.write(json.dumps(conf))
            sys.exit()
        elif x == '-cache':
            local_cache = True
    parse(local_cache)
            
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = base
import os
import json

from bibserver import dao
from bibserver.config import config

TESTDB = 'bibserver-test'

here = os.path.dirname(__file__)
fixtures_path = os.path.join(here, 'fixtures.json')
fixtures = json.load(open(fixtures_path))

config["ELASTIC_SEARCH_DB"] = TESTDB
dao.init_db()


class Fixtures(object):
    raw = fixtures

    @classmethod
    def create_account(cls):
        accountdict = dict(fixtures['accounts'][0])
        pw = accountdict['password_raw']
        del accountdict['password_raw']
        cls.account = dao.Account(**accountdict)
        cls.account.set_password(pw)
        cls.account.save()

__all__ = ['config', 'fixtures', 'Fixtures', 'dao', 'TESTDB', 'json']


########NEW FILE########
__FILENAME__ = test_dao
import os
import json
import pprint
from nose.tools import assert_equal

from test.base import fixtures, Fixtures, TESTDB
import bibserver.dao as dao
import bibserver.util as util
from datetime import datetime, timedelta

class TestDAO:
    @classmethod
    def setup_class(cls):
        Fixtures.create_account()

    @classmethod
    def teardown_class(cls):
        conn, db = dao.get_conn()
        conn.delete_index(TESTDB)

    def test_get_None(self):
        r = dao.Record.get(None)
        assert r == None
        
    def test_01_record(self):
        # Note, adding a one second negative delay to the timestamp
        # otherwise the comparison overflows when subtracting timestamps
        t1 = datetime.now() - timedelta(seconds=1)
        recdict = fixtures['records'][0]
        record = dao.Record.upsert(recdict)
        outrecord = dao.Record.get(record.id)
        for attr in ['type', 'author']:
            assert record[attr] == recdict[attr], record
            assert outrecord[attr] == recdict[attr], outrecord
        
        print outrecord.keys()
        assert '_created' in outrecord
        assert '_last_modified' in outrecord
        last_modified_in_record = outrecord['_last_modified']
        t2 = datetime.strptime(last_modified_in_record, r"%Y%m%d%H%M%S")
        difference = t2 - t1
        print last_modified_in_record, t1, t2, difference
        assert difference.seconds < 1
    
    def test_02_collection(self):
        label = u'My Collection'
        slug = util.slugify(label)
        colldict = {
            'label': label,
            'slug': slug,
            'owner': Fixtures.account.id
            }
        coll = dao.Collection.upsert(colldict)
        assert coll.id, coll
        assert coll['label'] == label
        # should only be one collection for this account so this is ok
        account_colls = Fixtures.account.collections
        assert coll.id == account_colls[0].id, account_colls
        
    def test_making_ids(self):
        recdict1 = fixtures['records'][0].copy()
        del recdict1['_id']
        recdict2 = recdict1.copy()
        recdict3 = recdict1.copy()
        recdict3['foobar'] = 'baz'
        a = dao.make_id(recdict1)
        b = dao.make_id(recdict3)
        print a
        print b
        assert a != b
        record1 = dao.Record.upsert(recdict1)
        record2 = dao.Record.upsert(recdict2)
        record3 = dao.Record.upsert(recdict3)
        print record1, '*'*5
        print record2, '*'*5
        print record3, '*'*5
        assert record1['_id'] == record2['_id']
        assert record1['_id'] != record3['_id']

class TestDAOQuery:
    @classmethod
    def setup_class(cls):
        for rec in fixtures['records']:
            dao.Record.upsert(rec)

    @classmethod
    def teardown_class(cls):
        conn, db = dao.get_conn()
        conn.delete_index(TESTDB)

    def test_query(self):
        out = dao.Record.query()
        assert out['hits']['total'] == 2

    def test_query_size(self):
        out = dao.Record.query(size=1)
        assert out['hits']['total'] == 2
        assert_equal(len(out['hits']['hits']), 1)

    def test_query_facet(self):
        facet_fields = [{'key':'type'}]
        out = dao.Record.query(facet_fields=facet_fields)
        print pprint.pprint(out)
        facetterms = out['facets']['type']['terms']
        assert len(facetterms) == 2
        assert facetterms[0]['term'] == 'book'
        assert facetterms[0]['count'] == 1

    def test_query_term(self):
        out = dao.Record.query(terms={'type': ['book']})
        assert_equal(out['hits']['total'], 1)


########NEW FILE########
__FILENAME__ = test_importer
from base import *

from bibserver.importer import Importer
import bibserver.dao
import os

class TestImporter:
    @classmethod
    def setup_class(cls):
        pass

    @classmethod
    def teardown_class(cls):
        conn, db = dao.get_conn()
        conn.delete_index(TESTDB)

    def test_upload(self):
        owner = dao.Account(id='testaccount1')
        owner.save()
        i = Importer(owner=owner)
        data = open('test/data/sample.bibtex.bibjson')
        collection_in = {
            'label': u'My Test Collection'
            }
        coll, records = i.upload(data, collection_in)
        assert coll.id
        assert owner.collections[0].id == coll.id, owner.collections

        assert len(records) == 1, records
        recid = records[0]['_id']
        out = bibserver.dao.Record.get(recid)
        assert out["year"] == '2008', out
        assert out['collection'] == coll['collection']

        # now try uploading exactly the same data again
        data = open('test/data/sample.bibtex.bibjson')
        newcoll, records = i.upload(data, collection_in)
        # still should have only one collection
        assert len(owner.collections) == 1
        assert newcoll.id == coll.id
        assert len(records) == 1
        assert records[0]['collection'] == coll['collection']
        # still should have only one record in it
        recs_for_collection = dao.Record.query('collection:"' + coll['collection'] + '"')
        assert recs_for_collection['hits']['total'] == 1, recs_for_collection


########NEW FILE########
__FILENAME__ = test_ingest
from test.base import fixtures, Fixtures, TESTDB
import bibserver.dao as dao
import nose.tools
from bibserver import ingest, dao
from bibserver.config import config
import os, json, subprocess

class TestIngest:
    @classmethod
    def setup_class(cls):
        Fixtures.create_account()
        config['download_cache_directory'] = 'test/data/downloads'
        # initialise the plugins
        ingest.init()
        assert 'bibtex' in ingest.PLUGINS

    @classmethod
    def teardown_class(cls):
        conn, db = dao.get_conn()
        conn.delete_index(TESTDB)
        for x in os.listdir('test/data/downloads'):
            os.unlink(os.path.join('test/data/downloads', x))
        os.rmdir('test/data/downloads')

    @nose.tools.raises(ingest.IngestTicketInvalidInit)
    def test_params(self):
        t = ingest.IngestTicket(owner='tester')

    @nose.tools.raises(ingest.IngestTicketInvalidOwnerException)
    def test_owner_none(self):
        t = ingest.IngestTicket(owner=None, 
                                    collection='test', format='json', source_url='')

    def test_owner_valid_01(self):
        unknown_owner = dao.Account.get('moocow')
        assert unknown_owner is None
        t = ingest.IngestTicket(owner='moocow',
                                    collection='test', format='json', source_url='')

    @nose.tools.raises(ingest.IngestTicketInvalidOwnerException)
    def test_owner_valid_02(self):
        t = ingest.IngestTicket(owner={}, 
                                    collection='test', format='json', source_url='')

    def test_download(self):
        # Note: the URL intentionally has a space at the end
        URL = 'https://raw.github.com/okfn/bibserver/master/test/data/sample.bibtex '
        t = ingest.IngestTicket(owner='tester', 
                                     collection='test', format='bibtex', source_url=URL)
        assert t['state'] == 'new'
        t.save()
        assert len(ingest.get_tickets()) == 1
        
        ingest.determine_action(t)
        assert t['state'] == 'downloaded'
        assert t['data_md5'] == 'b61489f0a0f32a26be4c8cfc24574c0e'

    def test_failed_download(self):
        t = ingest.IngestTicket(source_url='bogus_url',
                                    owner='tester', collection='test', format='json', )
        
        ingest.determine_action(t)
        assert t['state'] == 'failed'
        
    def test_get_tickets(self):
        tckts = ingest.get_tickets()
        assert len(tckts) > 0
        for t in tckts:
            assert 'tester/test,' in str(t)

    def test_parse_and_index(self):
        URL = 'https://raw.github.com/okfn/bibserver/master/test/data/sample.bibtex'
        t = ingest.IngestTicket(owner='tester', 
                                     collection=u'test', format='bibtex', source_url=URL)
        ingest.determine_action(t); print repr(t)
        assert t['state'] == 'downloaded'
        ingest.determine_action(t); print repr(t)
        assert t['state'] == 'parsed'
        ingest.determine_action(t); print repr(t)
        assert t['state'] == 'done'
        
        data_path = 'test/data/downloads/' + t['data_json']
        data = json.loads(open(data_path).read())
        assert data['records'][0]['title'] == 'Visibility to infinity in the hyperbolic plane, despite obstacles'
        
    def test_bibtex_empty_name(self):
        p = ingest.PLUGINS.get('bibtex')
        inp_data = '''@article{srising66,
        author="H. M. Srivastava and ",
        title="{zzz}",
        journal="zzz",
        volume=zzz,
        pages="zzz",
        year=zzz}'''
        p = subprocess.Popen(p['_path'], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = p.communicate(input=inp_data)[0]
        data = json.loads(data)
        assert len(data['records'][0]['author']) == 1
        
    def test_bibtex_utf(self):
        p = ingest.PLUGINS.get('bibtex')
        inp_data = open('test/data/sampleutf8.bibtex').read()
        p = subprocess.Popen(p['_path'], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = p.communicate(input=inp_data)[0]
        data = json.loads(data)
        assert data['records'][0]['title'] == u'\u201cBibliotheken fu\u0308r o\u0308ffnen\u201d'

    def test_bibtex_missing_comma(self):
        inp_data = '''@article{digby_mnpals_2011,
author = {Todd Digby and Stephen Elfstrand},
title = {{Open Source Discovery: Using VuFind to create MnPALS Plus}},
journal = {Computers in Libraries},
year = {2011},
month = {March}
}'''
        p = ingest.PLUGINS.get('bibtex')
        p = subprocess.Popen(p['_path'], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = p.communicate(input=inp_data)[0]
        data = json.loads(data)
        print repr(data['records'][0])
        assert 'month' not in data['records'][0]

    def test_bibtex_keywords(self):
        inp_data = '''@misc{Morgan2011,
            author = {Morgan, J. T. and Geiger, R. S. and Pinchuk, M. and Walker, S.},
            keywords = {open\_access, wrn2011, wrn201107, thing\#withhash},
            title = {{This is a test}},
            year = {2011}
        }
'''
        p = ingest.PLUGINS.get('bibtex')
        p = subprocess.Popen(p['_path'], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = p.communicate(input=inp_data)[0]
        data = json.loads(data)
        assert 'keyword' in data['records'][0]
        assert u'open_access' in data['records'][0].get('keyword'), data['records'][0].get('keyword')
        assert u'thing#withhash' in data['records'][0].get('keyword'), data['records'][0].get('keyword')

    def test_csv(self):
        p = ingest.PLUGINS.get('csv')
        inp_data = open('test/data/sample.csv').read()
        p = subprocess.Popen(p['_path'], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = p.communicate(input=inp_data)[0]
        data = json.loads(data)
        assert data['records'][0]['title'] == 'Visibility to infinity in the hyperbolic plane, despite obstacles'

    def test_BOM(self):
        csv_file = '''"bibtype","citekey","title","author","year","eprint","subject"
        "misc","arXiv:0807.3308","Visibility to infinity in the hyperbolic plane, despite obstacles","Itai Benjamini,Johan Jonasson,Oded Schramm,Johan Tykesson","2008","arXiv:0807.3308","sle"        
'''
        csv_file_with_BOM = '\xef\xbb\xbf' + csv_file
        p = ingest.PLUGINS.get('csv')
        pp = subprocess.Popen(p['_path'], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data1 = json.loads(pp.communicate(input=csv_file)[0])
        pp = subprocess.Popen(p['_path'], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data2 = json.loads(pp.communicate(input=csv_file_with_BOM)[0])

        assert data1['records'][0]['bibtype'] == data2['records'][0]['bibtype']

#
    def test_risparser_01(self):
        inp_data = open('test/data/sample.ris').read()
        p = ingest.PLUGINS.get('ris')
        p = subprocess.Popen(p['_path'], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = json.loads(p.communicate(input=inp_data)[0])
        data = data['records']
        assert len(data) == 240
        assert type(data[0]['title']) is unicode
        assert data[0]['title'] == u'Using Workflows to Explore and Optimise Named Entity Recognition for Chemisty'
        assert len(data[0]['author']) == 5
        data[0]['author'][0] = {'name': u'Kolluru, B.K.'}
        
    def test_risparser_runon_lines(self):
        inp_data = '''TY  - JOUR
AU  - Murray-Rust, P.
JF  - Org. Lett.
TI  - [Red-breasted 
  goose 
  colonies]
PG  - 559-68
'''
        p = ingest.PLUGINS.get('ris')
        p = subprocess.Popen(p['_path'], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = json.loads(p.communicate(input=inp_data)[0])
        data = data['records']
        assert data[0]['title'] == u'[Red-breasted goose colonies]'

    def test_json_01(self):
        inp_data = '''
{
    "records": [
        {
            "Comment": "haven't yet found an example of gratisOA beyond PMC deposition http://www.ncbi.nlm.nih.gov/pmc/?term=science%5Bjournal%5D", 
            "Publisher": "AAAS", 
            "links": [], 
            "Reporter": "Ross", 
            "Some Journals": "Science", 
            "Brand (if any)": "", 
            "link to oldest": "", 
            "cid": "2", 
            "Licence": "", 
            "title": "AAAS: Science", 
            "Number of articles affected": "", 
            "oldest gratis OA": ""
        }
]}
'''
        p = ingest.PLUGINS.get('json')
        p = subprocess.Popen(p['_path'], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = json.loads(p.communicate(input=inp_data)[0])
        data = data['records']
        assert data[0]['title'] == u'AAAS: Science'

    def test_plugin_dump(self):
        plugins = ingest.get_plugins()
        assert len(plugins.keys()) > 0

########NEW FILE########
__FILENAME__ = test_web
from nose.tools import assert_equal
import urllib
from base import *
from bibserver import web, ingest
import os


class TestWeb(object):
    @classmethod
    def setup_class(cls):
        web.app.config['TESTING'] = True
        cls.app = web.app.test_client()
        # fixture data
        recdict = fixtures['records'][0]
        cls.record = dao.Record.upsert(recdict)
        Fixtures.create_account()
        config['download_cache_directory'] = 'test/data/downloads'
        ingest.init()

    @classmethod
    def teardown_class(cls):
        conn, db = dao.get_conn()
        conn.delete_index(TESTDB)
        for x in os.listdir('test/data/downloads'):
            os.unlink(os.path.join('test/data/downloads', x))
        os.rmdir('test/data/downloads')

    def test_home(self):
        res = self.app.get('/')
        assert 'BibSoup' in res.data, res.data

    def test_faq(self):
        res = self.app.get('/faq')
        assert 'This service is an example' in res.data, res.data

    def test_record(self):
        res = self.app.get('/' + Fixtures.account.id + '/' + self.record["collection"] + '/' + self.record["_id"] + '.json')
        assert res.status == '200 OK', res.status
        out = json.loads(res.data)
        assert out["id"] == self.record["id"], out

    def test_upload(self):
        res = self.app.get('/upload')
        print res.status
        assert res.status == '302 FOUND', res.status
        res = self.app.get('/upload',
            headers={'REMOTE_USER': Fixtures.account.id}
            )
        assert res.status == '200 OK', res.status
        assert 'upload' in res.data, res.data

    def test_upload_post(self):
        startnum = dao.Record.query()['hits']['total']
        res = self.app.post('/upload?format=bibtex&collection='+urllib.quote_plus('"My Test Collection"'),
            data = {'upfile': (open('test/data/sample.bibtex'), 'sample.bibtex')},
            headers={'REMOTE_USER': Fixtures.account.id}
            )
        assert res.status == '302 FOUND', res.status
        # Now we have to trigger the ingest handling of the ticket
        # which is normally done asynchronously
        for state in ('new', 'downloaded', 'parsed'):
            for t in ingest.get_tickets(state):
                ingest.determine_action(t)
        
        endnum = dao.Record.query()['hits']['total']
        assert_equal(endnum, startnum+1)

    # TODO: re-enable
    # This does not work because login in the previous method appears to
    # persist to this method. Not sure how to fix this ...
    def _test_upload_post_401(self):
        bibtex_data = open('test/data/sample.bibtex').read()
        res = self.app.post('/upload',
            data=dict(
                format='bibtex',
                collection='My Test Collection',
                data=bibtex_data,
                )
            )
        assert res.status == '401 UNAUTHORIZED', res.status

    def test_query(self):
        res = self.app.get('/query')
        assert res.status == '200 OK', res.status

        res = self.app.get('/query?q=title:non-existent')
        assert res.status == '200 OK', res.status
        out = json.loads(res.data)
        assert out['hits']['total'] == 0, out

    def test_accounts_query_inaccessible(self):
        res = self.app.get('/query/account')
        assert res.status == '401 UNAUTHORIZED', res.status

    def test_search(self):
        res = self.app.get('/search?q=tolstoy&format=json')
        assert res.status == '200 OK', res.status
        out = json.loads(res.data)
        assert len(out) == 1, out
        assert "Tolstoy" in out[0]["author"][0]["name"], out

        


########NEW FILE########
