__FILENAME__ = handlers
import logging
import getpass
from datetime import datetime
from socket import gethostname
from pymongo.connection import Connection
from bson import InvalidDocument


class MongoFormatter(logging.Formatter):
    def format(self, record):
        """Format exception object as a string"""
        data = record.__dict__.copy()

        if record.args:
            record.msg = record.msg % record.args

        data.update(
            username=getpass.getuser(),
            time=datetime.now(),
            host=gethostname(),
            message=record.msg,
            args=tuple(unicode(arg) for arg in record.args)
        )
        if 'exc_info' in data and data['exc_info']:
            data['exc_info'] = self.formatException(data['exc_info'])
        return data
    

class MongoHandler(logging.Handler):
    """ Custom log handler

    Logs all messages to a mongo collection. This  handler is 
    designed to be used with the standard python logging mechanism.
    """

    @classmethod
    def to(cls, db, collection, host='localhost', port=None, level=logging.NOTSET):
        """ Create a handler for a given  """
        return cls(Connection(host, port)[db][collection], level)
        
    def __init__(self, collection, db='mongolog', host='localhost', port=None, level=logging.NOTSET):
        """ Init log handler and store the collection handle """
        logging.Handler.__init__(self, level)
        if (type(collection) == str):
            self.collection = Connection(host, port)[db][collection]
        else:
            self.collection = collection
        self.formatter = MongoFormatter()

    def emit(self,record):
        """ Store the record to the collection. Async insert """
        try:
            self.collection.save(self.format(record))
        except InvalidDocument, e:
            logging.error("Unable to save log record: %s", e.message ,exc_info=True)


########NEW FILE########
__FILENAME__ = simple_logging

import sys
sys.path.append('..')

import logging

from pymongo.connection import Connection
from mongolog.handlers import MongoHandler

if __name__ == '__main__':

    log = logging.getLogger('example')
    log.setLevel(logging.DEBUG)

    log.addHandler(MongoHandler.to('mongolog', 'log'))

    log.debug("1 - debug message")
    log.info("2 - info message")
    log.warn("3 - warn message")
    log.error("4 - error message")
    log.critical("5 - critical message")


########NEW FILE########
__FILENAME__ = test

import unittest

from tests import *

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_config

import unittest
import logging

from pymongo.connection import Connection

from os.path import dirname
from logging.config import fileConfig, dictConfig

class TestConfig(unittest.TestCase):
    def setUp(self):
        filename = dirname(__file__) + '/logging-test.config'
        fileConfig(filename)

        """ Create an empty database that could be used for logging """
        self.db_name = '_mongolog_test'
        self.collection_name = 'log_test'

        self.conn = Connection('localhost')
        self.conn.drop_database(self.db_name)

    def tearDown(self):
        """ Drop used database """
        self.conn.drop_database(self.db_name)
        
    def testLoggingFileConfiguration(self):
        log = logging.getLogger('example')
        log.debug('test')

        r = self.conn[self.db_name][self.collection_name]
    
        message = r.find_one({'level':'debug', 'msg':'test'})
        self.assertEquals(message['msg'], 'test')

class TestDictConfig(unittest.TestCase):
    def setUp(self):
        """ Create an empty database that could be used for logging """
        self.db_name = '_mongolog_test_dict'
        self.collection_name = 'log_test'

        self.configDict = {
            'version': 1,
            'handlers': {
                'mongo': {
                    'class': 'mongolog.handlers.MongoHandler',
                    'db': self.db_name,
                    'collection': self.collection_name,
                    'level': 'INFO'
                }
            },
            'root': {
                'handlers': ['mongo'],
                'level': 'INFO'
            }
        }

        self.conn = Connection('localhost')
        self.conn.drop_database(self.db_name)

    def testLoggingDictConfiguration(self):
        dictConfig(self.configDict)
        log = logging.getLogger('dict_example')
        log.debug('testing dictionary config')

        r = self.conn[self.db_name][self.collection_name]

        message = r.find_one({'level':'debug', 'msg':'dict_example'})
        self.assertEquals(message, None,
            "Logger put debug message in when info level handler requested")

        log.info('dict_example')
        message = r.find_one({'level':'info', 'msg':'dict_example'})
        self.assertNotEquals(message, None,
            "Logger didn't insert message into database")
        self.assertEquals(message['msg'], 'dict_example',
            "Logger didn't insert correct message into database")

    def tearDown(self):
        """ Drop used database """
        self.conn.drop_database(self.db_name)



########NEW FILE########
__FILENAME__ = test_handler
import unittest
import logging

from pymongo.connection import Connection

from mongolog.handlers import MongoHandler


class TestRootLoggerHandler(unittest.TestCase):
    """
    Test Handler attached to RootLogger
    """
    def setUp(self):
        """ Create an empty database that could be used for logging """
        self.db_name = '_mongolog_test'

        self.conn = Connection('localhost')
        self.conn.drop_database(self.db_name)

        self.db = self.conn[self.db_name]
        self.collection = self.db['log']

    def tearDown(self):
        """ Drop used database """
        self.conn.drop_database(self.db_name)
        

    def testLogging(self):
        """ Simple logging example """
        log = logging.getLogger('')
        log.setLevel(logging.DEBUG)

        log.addHandler(MongoHandler(self.collection))
        log.debug('test')

        r = self.collection.find_one({'levelname':'DEBUG', 'msg':'test'})
        self.assertEquals(r['msg'], 'test')

    def testLoggingException(self):
        """ Logging example with exception """
        log = logging.getLogger('')
        log.setLevel(logging.DEBUG)

        log.addHandler(MongoHandler(self.collection))

        try:
            1/0
        except ZeroDivisionError:
            log.error('test zero division', exc_info=True)

        r = self.collection.find_one({'levelname':'ERROR', 'msg':'test zero division'})
        self.assertTrue(r['exc_info'].startswith('Traceback'))

    def testQueryableMessages(self):
        """ Logging example with dictionary """
        log = logging.getLogger('query')
        log.setLevel(logging.DEBUG)

        log.addHandler(MongoHandler(self.collection))

        log.info({'address': '340 N 12th St', 'state': 'PA', 'country': 'US'})
        log.info({'address': '340 S 12th St', 'state': 'PA', 'country': 'US'})
        log.info({'address': '1234 Market St', 'state': 'PA', 'country': 'US'})
    
        cursor = self.collection.find({'level':'info', 'msg.address': '340 N 12th St'})
        self.assertEquals(cursor.count(), 1, "Expected query to return 1 "
            "message; it returned %d" % cursor.count())
        self.assertEquals(cursor[0]['msg']['address'], '340 N 12th St')

        cursor = self.collection.find({'level':'info', 'msg.state': 'PA'})

        self.assertEquals(cursor.count(), 3, "Didn't find all three documents")

########NEW FILE########
__FILENAME__ = settings

MONGO = {
    'db' : 'mongolog',
    'collection' : 'log',
    'host' : 'localhost',
    'port' : None
}


########NEW FILE########
__FILENAME__ = webui

import web

from pymongo.connection import Connection
from pymongo import ASCENDING, DESCENDING

import settings

urls = (
    '/(.*)', 'index'
)

def get_mongo_collection(db, collection, host, port):
    return Connection(host, port)[db][collection]

app = web.application(urls, globals())
render = web.template.render('templates/', base='base')
db = get_mongo_collection(**settings.MONGO)

class index:
    def GET(self, level):
        args = {}
        if level and level in ['info', 'debug', 'warning', 'error', 'critical']:
            args = {'level':level}

        def fill_missing(el):
            if not 'host' in el:
                el['host'] = '(unknow)'
            return el            
        logs = map(fill_missing, db.find(args, limit=100).sort('$natural', DESCENDING))

        return render.index(logs)

if __name__ == '__main__':
    app.run()


########NEW FILE########
