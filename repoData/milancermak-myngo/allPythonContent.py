__FILENAME__ = actions
# -*- coding: utf-8 -*-

from handlers import BaseHandler
from pymongo.son import SON
import tornado.web

#
# DB actions
#
class CloneDatabase(BaseHandler):

    def post(self):
        original = self.get_argument('original')
        new = self.get_argument('new')
        cmd = SON([('copydb', 1),
                   ('fromdb', original),
                   ('todb', new)])
        result = self.c['admin'].command(cmd, check=False)
        self.respond_back_result(result)


class DropDatabase(BaseHandler):

    def post(self):
        db = self.get_argument('db')
        cmd = SON(data={'dropDatabase': 1})
        result = self.c[db].command(cmd, check=False)
        self.respond_back_result(result)


class RepairDatabase(BaseHandler):

    def post(self):
        db = self.get_argument('db')
        cmd = SON(data={'repairDatabase': 1})
        result = self.c[db].command(cmd, check=False)
        self.respond_back_result(result)


#
# Collection Actions
#
class DropCollection(BaseHandler):

    def post(self):
        db = self.get_argument('db')
        coll = self.get_argument('coll')
        self.c[db].drop_collection(coll)
        self.respond_back_result({'ok': 1})


class RenameCollection(BaseHandler):

    def post(self):
        db = self.get_argument('db')
        original = self.get_argument('original')
        new = self.get_argument('new')
        self.c[db][original].rename(new)
        self.respond_back_result({'ok': 1})


class ValidateCollection(BaseHandler):

    def post(self):
        db = self.get_argument('db')
        coll = self.get_argument('coll')
        cmd = SON(data={'validate': coll})
        result = self.c[db].command(cmd, check=False)
        result['result'] = '<pre>'+result['result']+'</pre>' # format the string
        self.respond_back_result(result)
    

urls = [(r'/x_clone_db/?$', CloneDatabase),
        (r'/x_drop_db/?$', DropDatabase),
        (r'/x_repair_db/?$', RepairDatabase),
        (r'/x_drop_coll/?$', DropCollection),
        (r'/x_rename_coll/?$', RenameCollection),
        (r'/x_validate_coll/?$', ValidateCollection),
        ]


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

import os
import base64

PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))

DEBUG = True

PORT = 8000

SECRET = base64.b64encode(os.urandom(32))

TEMPLATE_PATH = os.path.join(PROJECT_PATH, 'templates')
STATIC_PATH = os.path.join(PROJECT_PATH, 'static')

# MongoDB
MONGO_PORT = 27017
MONGO_HOST = 'localhost'

########NEW FILE########
__FILENAME__ = handlers
# -*- coding: utf-8 -*-

import conf
import pp
import pymongo
import os
import tornado.web
import bson

try:
    import simplejson as json
except ImportError:
    import json

class BaseHandler(tornado.web.RequestHandler):

    @property
    def c(self):
        return pymongo.Connection(conf.MONGO_HOST, conf.MONGO_PORT)

    def render(self, template_name, **kwargs):
        kwargs.update({'format': pp})
        if not kwargs.get('nav_section'):
            kwargs.update({'nav_section': 'db'})
        path = os.path.join(conf.TEMPLATE_PATH, template_name)
        super(BaseHandler, self).render(path, **kwargs)

    def respond_back_result(self, result):
        """ Transforms MongoDB command result to JSON. """
        rok = int(result['ok'])
        if rok == 1:
            res = {'success': True}
            res.update(result)
            self.write(json.dumps(res))
        else:
            self.write(json.dumps({'success': False}))

        self.finish()


class DatabaseHandler(BaseHandler):

    def get(self):
        # TODO: add auth
        table = {'headers': ('DB names', 'Collections', 'Actions'),
                 'rows': [[db, self.c[db].collection_names()] for db in self.c.database_names()]}
        self.render('db_list.html', table=table)


class CollectionHandler(BaseHandler):

    def get(self, db_name):
        table = {'headers': ('Name', 'No. of documents', 'Actions'),
                 'rows': [[coll, self.c[db_name][coll].count()]
                          for coll in self.c[db_name].collection_names()]}
        self.render('coll_list.html', table=table, db_name=db_name)


class CollectionDetailHandler(BaseHandler):

    def get(self, db_name, coll_name):
        # TODO: collections; sort by object IDs, column will be all top-level keys
        page = self.get_argument('page', 0)
        #sort_by = self.get_argument('sort_by')
        cursor = self.c[db_name][coll_name].find()
        objects = cursor.sort('_id').skip(page * 50).limit(50)

        # TODO: decide if to use own fork of Tornado with sessions
        #       as so I could easily display columns, remember sorting
        #       direction etc.
        #       OK, this may not be necessary; check this documtent
        #       http://www.mongodb.org/display/DOCS/UI and Futon for CouchDB
        #       to get inspiration on what features to implement
            
        #count = cursor.count()        
        cols = [col for col in objects[0].keys() if col!="_id" ][:15]
        table = { 'headers': cols, 'rows': objects, 
                'db_name': db_name, 'coll_name': coll_name }
        self.render('obj_list.html', table=table)

class ObjectDetailHandler(BaseHandler):
    def get(self, db_name, coll_name, rec_id):
        obj = self.c[db_name][coll_name].find_one({'_id': bson.ObjectId(rec_id)})
        table = { 'items': obj.items() }
        self.render('obj_detail.html', table=table)

class LogHandler(BaseHandler):
    pass


class ShellHandler(BaseHandler):
    pass


class ServerInfoHandler(BaseHandler):

    def get(self):
        si = self.c.server_info()
        server_data = {'version': si['version'],
                       'status': si['ok'],
                       'host': self.c.host,
                       'port': self.c.port,
                       'system': si['sysInfo']}
        replication_data = {}
        sharding_data = {}
        self.render('server_info.html',
                    server_data=server_data,
                    replication_data=replication_data,
                    sharding_data=sharding_data,
                    nav_section='si')


urls = [(r'/', DatabaseHandler),
        (r'/_log/?$', LogHandler),
        (r'/_shell/?$', ShellHandler),
        (r'/_server/?$', ServerInfoHandler),
        (r'/(?P<db_name>[^_]\S+)/(?P<coll_name>\S+[^/])/(?P<rec_id>\S+[^/])/?$', ObjectDetailHandler),
        (r'/(?P<db_name>[^_]\S+)/(?P<coll_name>\S+[^/])/?$', CollectionDetailHandler),
        (r'/(?P<db_name>[^_]\S+[^/])/?$', CollectionHandler),
        ]

########NEW FILE########
__FILENAME__ = pp
# -*- coding: utf-8 -*-

# template pretty printers

def pprint_list(l):
    return ', '.join(l)

########NEW FILE########
__FILENAME__ = run
# -*- coding: utf-8 -*-

import actions
import conf
import handlers
import tornado
import tornado.httpserver
import tornado.web

class Myngo(tornado.web.Application):

    def __init__(self):
        settings = {'cookie_secret': conf.SECRET,
                    'xsrf_cookies': True,
                    'template_path': conf.TEMPLATE_PATH,
                    'static_path': conf.STATIC_PATH,
                    'debug': conf.DEBUG}
        # super(Myngo, self).__init__(handlers, **settings)
        tornado.web.Application.__init__(self, actions.urls+handlers.urls, **settings)

def run():
    server = tornado.httpserver.HTTPServer(Myngo())
    server.listen(conf.PORT)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    run()
        

########NEW FILE########
