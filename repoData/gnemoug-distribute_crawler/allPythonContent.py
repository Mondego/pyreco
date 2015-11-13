__FILENAME__ = clear_stats
#!/usr/bin/python
#-*-coding:utf-8-*-

"""
    After you run the project every time,the stats infomation in still in the redis database.
    
    Run this file can help you clear the stats in the redis database.
"""

import redis

# default values
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
STATS_KEY = 'scrapy:stats'

def clear_stats():
    server = redis.Redis(REDIS_HOST, REDIS_PORT)
    server.delete(STATS_KEY)

if __name__ == "__main__":
    clear_stats()

########NEW FILE########
__FILENAME__ = compression
#!/usr/bin/python
#-*-coding:utf8-*-

"""
    compress all the zip and rar files in the specific directory.
"""

import os
import zipfile
import traceback
import argparse
import shutil
from pprint import pprint

def Compress_zip(raw_dir):
    """
        Compress_zip
    """
    target_zipfile = raw_dir + ".zip"
    cmd = 'zip -r -j "'+target_zipfile+'" '+' "'+raw_dir+'"'
    os.system(cmd)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d","--delsource",action='store_true',help="delete the source directory")
    args = parser.parse_args()

    path = os.path.abspath(os.path.dirname(__file__)) + "/../media/book_files"
    compress_paths = []
    for i in os.listdir(path):
        compress_paths.extend([os.path.join(path,i,j) for j in os.listdir(os.path.join(path,i))])

    #pprint(compress_paths)
    
    for i in compress_paths:
        Compress_zip(i)
    
    if args.delsource:#To ues this:python compression -d
        for i in compress_paths:
            shutil.rmtree(i,True)

########NEW FILE########
__FILENAME__ = decomperssion
#!/usr/bin/python
#-*-coding:utf8-*-

"""
    Decompression all the zip and rar files in the specific directory.
"""

import os
import zipfile
import traceback
import argparse
from pprint import pprint

def find_path_file(specific_file,search_directory):
    """
    result_path_filename
    """
    result_path_filename = list()
    result_path_filename.extend([os.path.join(dirpath,filename) for dirpath,dirnames,filenames in os.walk(search_directory) for filename in filenames if os.path.splitext(filename)[1] == ('.' + specific_file)])
    return result_path_filename

def Decompression_rar(specific_file):
    """
        Decompression_rar
        
        if you want use this function,you need install unrar,for ubuntu:
            sudo apt-get install unrar
            
        another decomperssion method is to use:rarfile,for help you can visit:
            http://www.pythonclub.org/python-files/rar
    """
    cmd='unrar x "'+specific_file+'"'+' "'+os.path.split(specific_file)[0]+'"'
    os.system(cmd)


def Decompression_zip(specific_file):
    """
        Decompression_zip
    """
    if zipfile.is_zipfile(specific_file):
        try:
            zipfile.ZipFile(specific_file).extractall(os.path.split(specific_file)[0])
        except Exception as err:
            traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d","--delsource",action='store_true',help="delete the source file(rar or zip)")
    args = parser.parse_args()

    path = os.path.abspath(os.path.dirname(__file__)) + "/../media/book_files"

    _rar = find_path_file('rar',path)
    for i in _rar:
        Decompression_rar(i)
    
    _zip = find_path_file('zip',path)
    for i in _zip:
        Decompression_zip(i)

    if args.delsource:
        _delete_rar = find_path_file('rar',path)
        _delete_zip = find_path_file('zip',path)
        for i in _delete_rar:
            os.remove(i)
        for i in _delete_zip:
            os.remove(i)

########NEW FILE########
__FILENAME__ = init_sharding_mongodb
#!/usr/bin/python
#-*-coding:utf-8-*-

"""
    This file is for initiate mongodb situation
    
    When you want to save book file in gridfs,then you need a sharding cluster,that the database design is:
    database:books_mongo
    collections:
        book_detail
        book_file
    fields:
        book_detail:
            book_name:string
            alias_name:vector
            author:vector
            book_description:string
            book_covor_image_url:string
            book_covor_image_path:string
            book_download:vector
            book_file_id:gridfs id
            book_file_url:string
            original_url:string
            update_time:datetime
        book_file:
            book_file.chunks:
                _id
                files_id
                n
                data
            book_file.files:
                _id
                length
                chunkSize
                uploadDate
                md5
                filename
                contentType
                aliases
                metadata
    index:
        book_name
        alias_name
        author
    sharding key:
        update_time+book_name

    So what this do is to delete books_mongo if it has existed,and initiate the sharding cluster.
    
    NOTE:
    For killall mongo procs after terminate the file process,you need use CTRL+C.
    Before you run this file,you need type this in a shell:sudo killall mongod.
    For check the info about all mongos,use the command:netstat -lntp|grep mongo
    
    ABOUT:
    This code mostly comes from:
        https://github.com/gnemoug/mongo-snippets/blob/master/sharding/simple-setup.py
"""

import os
import sys
import shutil
import pymongo
import types
#The atexit module defines a single function to register cleanup functions. 
import atexit

from socket import error, socket, AF_INET, SOCK_STREAM
from pymongo import ASCENDING, DESCENDING
from pymongo import MongoClient
from select import select
from subprocess import Popen, PIPE, STDOUT
from threading import Thread
from time import sleep

try:
    # new pymongo
    from bson.son import SON
except ImportError:
    # old pymongo
    from pymongo.son import SON#the Serialized Ocument Notation

# BEGIN CONFIGURATION

# some settings can also be set on command line. start with --help to see options

ShardMONGODB_DB = "books_mongo"
GridFs_Collection = "book_file"

BASE_DATA_PATH='/data/db/books/sharding/' #warning: gets wiped every time you run this
MONGO_PATH=os.getenv( "MONGO_HOME" , os.path.expanduser('~/10gen/mongo/') )
N_SHARDS=3
N_CONFIG=1 # must be either 1 or 3
N_MONGOS=1
CHUNK_SIZE=64 # in MB (make small to test splitting)
MONGOS_PORT=27017 if N_MONGOS == 1 else 10000 # start at 10001 when multi
USE_SSL=False # set to True if running with SSL enabled

CONFIG_ARGS=[]
MONGOS_ARGS=[]
MONGOD_ARGS=[]

# Note this reports a lot of false positives.
USE_VALGRIND=False
VALGRIND_ARGS=["valgrind", "--log-file=/tmp/mongos-%p.valgrind", "--leak-check=yes", 
               ("--suppressions="+MONGO_PATH+"valgrind.suppressions"), "--"]

# see http://pueblo.sourceforge.net/doc/manual/ansi_color_codes.html
CONFIG_COLOR=31 #red
MONGOS_COLOR=32 #green
MONGOD_COLOR=36 #cyan
BOLD=True
conn = None

INDEX = {\
            #collection
            'book_detail':\
                {\
                    #Unique indexes on sharded collections have to start with the shard key.
                    #You can have only one unique key in sharding configuration. 
                    (('book_name',ASCENDING),('author',ASCENDING)):{'name':'book_name_author'},
                    'book_name':{'name':'book_name'},
                    'author':{'name':'author'},
                    'alias_name':{'name':'alias_name'},
                }\
        }

# defaults -- can change on command line
COLLECTION_KEYS = {'book_detail':'update_time,book_name'}

def AFTER_SETUP():
    """
        make index and shard keys.
    """
    
    # feel free to change any of this
    # admin and conn are both defined globaly
    admin.command('enablesharding', ShardMONGODB_DB)

    for (collection, keystr) in COLLECTION_KEYS.iteritems():
        key=SON((k,1) for k in keystr.split(','))
        admin.command('shardcollection', ShardMONGODB_DB+'.'+collection, key=key)

    admin.command('shardcollection', ShardMONGODB_DB+'.'+GridFs_Collection+'.files', key={'_id':1})
    admin.command('shardcollection', ShardMONGODB_DB+'.'+GridFs_Collection+'.chunks', key={'files_id':1})
    
    for k,v in INDEX.items():
        for key,kwargs in v.items():
            conn[ShardMONGODB_DB][k].ensure_index(list(key) if type(key)==types.TupleType else key,**kwargs)

# END CONFIGURATION

for x in sys.argv[1:]:
    opt = x.split("=", 1)
    if opt[0] != '--help' and len(opt) != 2:
        raise Exception("bad arg: " + x )
    
    if opt[0].startswith('--'):
        opt[0] = opt[0][2:].lower()
        if opt[0] == 'help':
            print sys.argv[0], '[--help] [--chunksize=200] [--port=27017] [--path=/where/is/mongod] [collection=key]'
            sys.exit()
        elif opt[0] == 'chunksize':
            CHUNK_SIZE = int(opt[1])
        elif opt[0] == 'port':
            MONGOS_PORT = int(opt[1])
        elif opt[0] == 'path':
            MONGO_PATH = opt[1]
        elif opt[0] == 'usevalgrind': #intentionally not in --help
            #use for memory leak check.
            USE_VALGRIND = int(opt[1])
        else:
            raise( Exception("unknown option: " + opt[0] ) )
    else:
        COLLECTION_KEYS[opt[0]] = opt[1]

if MONGO_PATH[-1] != '/':
    MONGO_PATH = MONGO_PATH+'/'

print( "MONGO_PATH: " + MONGO_PATH )

if not USE_VALGRIND:
    VALGRIND_ARGS = []

# fixed "colors"
RESET = 0
INVERSE = 7

if os.path.exists(BASE_DATA_PATH):
    print( "removing tree: %s" % BASE_DATA_PATH )
    shutil.rmtree(BASE_DATA_PATH)

mongod = MONGO_PATH + 'mongod'
mongos = MONGO_PATH + 'mongos'

devnull = open('/dev/null', 'w+')

fds = {}
procs = []

def killAllSubs():
    for proc in procs:
        try:
            proc.terminate()
        except OSError:
            pass #already dead
atexit.register(killAllSubs)

def mkcolor(colorcode): 
    base = '\x1b[%sm'
    if BOLD:
        return (base*2) % (1, colorcode)
    else:
        return base % colorcode

def ascolor(color, text):
    return mkcolor(color) + text + mkcolor(RESET)

def waitfor(proc, port):
    trys = 0
    while proc.poll() is None and trys < 40: # ~10 seconds
        trys += 1
        s = socket(AF_INET, SOCK_STREAM)
        try:
            try:
                s.connect(('localhost', port))
                return
            except (IOError, error):
                sleep(5)
                #XXX:
                #When I use the sharding/simple-setup.py file,it always say:failed to start.But when I change the sleep time from 0.25 to 5,It works!
        finally:
            s.close()

    #extra prints to make line stand out
    print
    print proc.prefix, ascolor(INVERSE, 'failed to start')
    print
    
    sleep(1)
    killAllSubs()
    sys.exit(1)


def printer():
    while not fds: sleep(0.01) # wait until there is at least one fd to watch

    while fds:
        (files, _ , errors) = select(fds.keys(), [], fds.keys(), 1)
        for file in set(files + errors):
            # try to print related lines together
            while select([file], [], [], 0)[0]:
                line = file.readline().rstrip()
                if line:
                    print fds[file].prefix, line
                else:
                    if fds[file].poll() is not None:
                        print fds[file].prefix, ascolor(INVERSE, 'EXITED'), fds[file].returncode
                        del fds[file]
                        break
                break

printer_thread = Thread(target=printer)
printer_thread.start()


configs = []
for i in range(1, N_CONFIG+1):
    path = BASE_DATA_PATH +'config_' + str(i)
    os.makedirs(path)
    #print mongod,' --port ',str(20000+i),' --configsvr',' --dbpath ',path
    config = Popen([mongod, '--port', str(20000 + i), '--configsvr', '--dbpath', path] + CONFIG_ARGS, 
                   stdin=devnull, stdout=PIPE, stderr=STDOUT)
    config.prefix = ascolor(CONFIG_COLOR, 'C' + str(i)) + ':'
    fds[config.stdout] = config
    procs.append(config)
    waitfor(config, 20000 + i)
    configs.append('localhost:' + str(20000 + i))


for i in range(1, N_SHARDS+1):
    path = BASE_DATA_PATH +'shard_' + str(i)
    os.makedirs(path)
    shard = Popen([mongod, '--port', str(30000 + i), '--shardsvr', '--dbpath', path] + MONGOD_ARGS,
                  stdin=devnull, stdout=PIPE, stderr=STDOUT)
    shard.prefix = ascolor(MONGOD_COLOR, 'M' + str(i)) + ':'
    fds[shard.stdout] = shard
    procs.append(shard)
    waitfor(shard, 30000 + i)


#this must be done before starting mongos
for config_str in configs:
    host, port = config_str.split(':')
    config = MongoClient(host, int(port), ssl=USE_SSL).config
    config.settings.save({'_id':'chunksize', 'value':CHUNK_SIZE}, safe=True)
del config #don't leave around connection directly to config server

if N_MONGOS == 1:
    MONGOS_PORT -= 1 # added back in loop

for i in range(1, N_MONGOS+1):
    router = Popen(VALGRIND_ARGS + [mongos, '--port', str(MONGOS_PORT+i), '--configdb' , ','.join(configs)] + MONGOS_ARGS,
                   stdin=devnull, stdout=PIPE, stderr=STDOUT)
    router.prefix = ascolor(MONGOS_COLOR, 'S' + str(i)) + ':'
    fds[router.stdout] = router
    procs.append(router)

    waitfor(router, MONGOS_PORT + i)

conn = MongoClient('localhost', MONGOS_PORT + 1, ssl=USE_SSL)
admin = conn.admin

for i in range(1, N_SHARDS+1):
    admin.command('addshard', 'localhost:3000'+str(i), allowLocal=True)

AFTER_SETUP()

# just to be safe
sleep(2)

print '*** READY ***'
print 
print 

try:
    printer_thread.join()
except KeyboardInterrupt:
    pass

########NEW FILE########
__FILENAME__ = init_single_mongodb
#!/usr/bin/python
#-*-coding:utf-8-*-

"""
    This file is for initiate mongodb situation
    
    When you want to save book file in file system,then you don't need sharding cluster,that the database design is:
    database:books_fs
    collections:book_detail
    fields:
        book_detail:
            book_name
            alias_name:vector
            author:vector
            book_description:string
            book_covor_image_path:string
            book_covor_image_url:string
            book_download:vector
            book_file_url:string
            book_file:string
            original_url:string
            update_time:datetime
    index:
        book_name
        alias_name
        author

    So what this do is to delete books_fs is it has existed,and create index for it.
"""

import types
from pymongo.connection import MongoClient
from pymongo import ASCENDING, DESCENDING

DATABASE_NAME = "books_fs"
client = None
DATABASE_HOST = "localhost"
DATABASE_PORT = 27017
INDEX = {\
            #collection
            'book_detail':\
                {\
                    (('book_name',ASCENDING),('author',ASCENDING)):{'name':'book_name_author','unique':True},
                    'book_name':{'name':'book_name'},
                    'author':{'name':'author'},
                    'alias_name':{'name':'alias_name'},
                }\
        }

def drop_database(name_or_database):
    if name_or_database and client:
        client.drop_database(name_or_database)

def create_index():
    """
        create index for books_fs.book_detail
    """
    for k,v in INDEX.items():
        for key,kwargs in v.items():
            client[DATABASE_NAME][k].ensure_index(list(key) if type(key)==types.TupleType else key,**kwargs)

if __name__ == "__main__":
    client = MongoClient(DATABASE_HOST,DATABASE_PORT) 
    drop_database(DATABASE_NAME)
    create_index() 

########NEW FILE########
__FILENAME__ = google_cache
#!/usr/bin/python
#-*-coding:utf-8-*-

from urlparse import urlparse
from scrapy.http import Request
from scrapy.utils.python import WeakKeyCache

class GoogleCacheMiddleware(object):
    """
        this middleware allow spider to crawl the spicific domain url in google caches.

        you can define the GOOGLE_CACHE_DOMAINS in settings,it is a list which you want to visit the google cache.Or you can define a google_cache_domains in your spider and it is as the highest priority.
    """
    google_cache = 'http://webcache.googleusercontent.com/search?q=cache:'

    def __init__(self, cache_domains=''):
        self.cache = WeakKeyCache(self._cache_domains)
        self.cache_domains = cache_domains

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings['GOOGLE_CACHE_DOMAINS'])

    def _cache_domains(self, spider):
        if hasattr(spider, 'google_cache_domains'):
            return spider.google_cache_domains
        elif self.cache_domains:
            return self.cache_domains

        return ""

    def process_request(self, request, spider):
        """
            the scrapy documention said that:
                If it returns a Request object, the returned request will be rescheduled (in the Scheduler) to be downloaded in the future. The callback of the original request will always be called. If the new request has a callback it will be called with the response downloaded, and the output of that callback will then be passed to the original callback. If the new request doesn’t have a callback, the response downloaded will be just passed to the original request callback.
             but actually is that if it returns a Request object,then the original request will be droped,so you must make sure that the new request object's callback is the original callback.
        """
        gcd = self.cache[spider]
        if gcd:
            if urlparse(request.url).netloc in gcd:
                request = request.replace(url=self.google_cache + request.url)
                #request = Request(self.google_cache + request.url,request.callback)
                request.meta['google_cache'] = True
                return request
      
    def process_response(self, request, response, spider):

        if request.meta.get('google_cache',False):
            return response.replace(url = response.url[len(self.google_cache):]) 

        return response

########NEW FILE########
__FILENAME__ = rotate_useragent
#!/usr/bin/python
#-*-coding:utf-8-*-

import random
from scrapy.contrib.downloadermiddleware.useragent import UserAgentMiddleware

class RotateUserAgentMiddleware(UserAgentMiddleware):
    """
        a useragent middleware which rotate the user agent when crawl websites
        
        if you set the USER_AGENT_LIST in settings,the rotate with it,if not,then use the default user_agent_list attribute instead.
    """

    #the default user_agent_list composes chrome,I E,firefox,Mozilla,opera,netscape
    #for more user agent strings,you can find it in http://www.useragentstring.com/pages/useragentstring.php
    user_agent_list = [\
        'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31',\
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.60 Safari/537.17',\
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1309.0 Safari/537.17',\
        \
        'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)',\
        'Mozilla/5.0 (Windows; U; MSIE 7.0; Windows NT 6.0; en-US)',\
        'Mozilla/5.0 (Windows; U; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727)',\
        \
        'Mozilla/6.0 (Windows NT 6.2; WOW64; rv:16.0.1) Gecko/20121011 Firefox/16.0.1',\
        'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:15.0) Gecko/20100101 Firefox/15.0.1',\
        'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:15.0) Gecko/20120910144328 Firefox/15.0.2',\
        \
        'Mozilla/5.0 (Windows; U; Windows NT 6.1; rv:2.2) Gecko/20110201',\
        'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9a3pre) Gecko/20070330',\
        'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.13; ) Gecko/20101203',\
        \
        'Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14',\
        'Opera/9.80 (X11; Linux x86_64; U; fr) Presto/2.9.168 Version/11.50',\
        'Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; de) Presto/2.9.168 Version/11.52',\
        \
        'Mozilla/5.0 (Windows; U; Win 9x 4.90; SG; rv:1.9.2.4) Gecko/20101104 Netscape/9.1.0285',\
        'Mozilla/5.0 (Macintosh; U; PPC Mac OS X Mach-O; en-US; rv:1.8.1.7pre) Gecko/20070815 Firefox/2.0.0.6 Navigator/9.0b3',\
        'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.12) Gecko/20080219 Firefox/2.0.0.12 Navigator/9.0.0.6',\
    ]

    def __init__(self, user_agent=''):
        self.user_agent = user_agent

    def _user_agent(self, spider):
        if hasattr(spider, 'user_agent'):
            return spider.user_agent
        elif self.user_agent:
            return self.user_agent

        return random.choice(self.user_agent_list)

    def process_request(self, request, spider):
        ua = self._user_agent(spider)
        if ua:
            request.headers.setdefault('User-Agent', ua)

########NEW FILE########
__FILENAME__ = items
#!/usr/bin/python
#-*-coding:utf-8-*-

from scrapy.item import Item, Field

class WoaiduCrawlerItem(Item):
    mongodb_id = Field()
    book_name = Field()
    alias_name = Field()
    author = Field()
    book_description = Field()
    book_covor_image_path = Field()
    book_covor_image_url = Field()
    book_download = Field()
    book_file_url = Field()
    book_file = Field()#only use for save tho single mongodb
    book_file_id = Field()#only use for save to shard mongodb
    original_url = Field()

########NEW FILE########
__FILENAME__ = bookfile
#!/usr/bin/python
#-*-coding:utf-8-*-

import os
import itertools
from scrapy import log
from scrapy.item import Item
from pprint import pprint
from scrapy.http import Request
from woaidu_crawler.utils import color
from scrapy.utils.misc import arg_to_iter
from twisted.internet.defer import Deferred, DeferredList
from woaidu_crawler.utils.select_result import list_first_item
from woaidu_crawler.pipelines.file import FilePipeline,FSFilesStore,FileException
from scrapy.exceptions import DropItem, NotConfigured

class NofilesDrop(DropItem):
    """Product with no files exception"""
    def __init__(self, original_url="", *args):
        self.original_url = original_url
        self.style = color.color_style()
        DropItem.__init__(self, *args)

    def __str__(self):#####for usage: print e
        print self.style.ERROR("DROP(NofilesDrop):" + self.original_url)

        return DropItem.__str__(self)

class BookFileException(FileException):
    """General book file error exception"""

class FSBookFilesStore(FSFilesStore):
    pass

class WoaiduBookFile(FilePipeline):
    """
        This is for download the book file and then define the book_file 
        field to the file's path in the file system.
    """

    MEDIA_NAME = 'bookfile'
    EXPIRES = 90
    BOOK_FILE_CONTENT_TYPE = []
    URL_GBK_DOMAIN = []
    ATTACHMENT_FILENAME_UTF8_DOMAIN = []
    STORE_SCHEMES = {
        '': FSBookFilesStore,
        'file': FSBookFilesStore,
    }
    
    FILE_EXTENTION = ['.doc','.txt','.docx','.rar','.zip','.pdf']

    def __init__(self,store_uri,download_func=None):
        super(WoaiduBookFile, self).__init__(store_uri=store_uri,download_func=download_func)
        if not store_uri:
            raise NotConfigured
        self.bookfile_store = store_uri
        self.store = self._get_store(store_uri)
        self.item_download = {}

    @classmethod
    def from_settings(cls, settings):
        cls.EXPIRES = settings.getint('BOOK_FILE_EXPIRES', 90)
        cls.BOOK_FILE_CONTENT_TYPE = settings.get('BOOK_FILE_CONTENT_TYPE',[])
        cls.ATTACHMENT_FILENAME_UTF8_DOMAIN = settings.get('ATTACHMENT_FILENAME_UTF8_DOMAIN',[])
        cls.URL_GBK_DOMAIN = settings.get('URL_GBK_DOMAIN',[])
        cls.FILE_EXTENTION = settings.get('FILE_EXTENTION',[])
        store_uri = settings['BOOK_FILE_STORE']
        return cls(store_uri)

    def process_item(self, item, spider):
        """
            custom process_item func,so it will manage the Request result.
        """
        
        info = self.spiderinfo[spider]
        requests = arg_to_iter(self.get_media_requests(item, info))
        dlist = [self._process_request(r, info) for r in requests]
        dfd = DeferredList(dlist, consumeErrors=1)
        dfd.addCallback(self.item_completed, item, info)
        return dfd.addCallback(self.another_process_item, item, info)

    def another_process_item(self, result, item, info):
        """
            custom process_item func,so it will manage the Request result.
        """
        
        assert isinstance(result, (Item, Request)), \
                    "WoaiduBookFile pipeline' item_completed must return Item or Request, got %s" % \
                    (type(result))
        if isinstance(result,Item):
            return result
        elif isinstance(result,Request):
            dlist = [self._process_request(r, info) for r in arg_to_iter(result)]
            dfd = DeferredList(dlist, consumeErrors=1)
            dfd.addCallback(self.item_completed, item, info)
            #XXX:This will cause one item maybe return many times,it depends on how many 
            #times the download url failed.But it doesn't matter.Because when raise errors,
            #the items are no longer processed by further pipeline components.And when all
            #url download failed we can drop that item which book_file or book_file_url are
            #empty.
            return dfd.addCallback(self.another_process_item, item, info)
        else:
            raise NofilesDrop

    def get_media_requests(self, item, info):
        """
            Only download once per book,so it pick out one from all of the download urls.
        """ 
        
        #XXX:To test specific url,you can use the following method:
        #return Request("http://down.wmtxt.com/wmtxt/wmtxt/UploadFile/2010-6/%A1%B6%D3%F6%BC%FB%C4%E3%A1%B7.rar")
        if item.get('book_download'):
            downloadfile_urls = [i['url'] for i in item.get('book_download') if i['url']]
            downloadfile_urls = list(set(itertools.chain(*downloadfile_urls)))
            first_download_file = list_first_item(downloadfile_urls)
            self.item_download[item['original_url']] = downloadfile_urls[1:]
            if first_download_file:
                return Request(first_download_file)

    def item_completed(self, results, item, info):
        if self.LOG_FAILED_RESULTS:
            msg = '%s found errors proessing %s' % (self.__class__.__name__, item)
            for ok, value in results:
                if not ok:
                    log.err(value, msg, spider=info.spider)

        bookfile_paths_urls = [(x['path'],x['url']) for ok, x in results if ok]
        bookfile_path_url = list_first_item(bookfile_paths_urls)
        if bookfile_path_url:
            item['book_file'] = os.path.join(os.path.abspath(self.bookfile_store),bookfile_path_url[0])
            item['book_file_url'] = bookfile_path_url[1]
            return item
        else:
            if self.item_download[item['original_url']]:
                next = list_first_item(self.item_download[item['original_url']])
                self.item_download[item['original_url']] = self.item_download[item['original_url']][1:]
                return Request(next)
            else:
                return item
        
    def is_valid_content_type(self,response):
        """
            judge whether is it a valid response by the Content-Type.
        """
        content_type = response.headers.get('Content-Type','')
        
        return content_type not in self.BOOK_FILE_CONTENT_TYPE

########NEW FILE########
__FILENAME__ = cover_image
#!/usr/bin/python
#-*-coding:utf-8-*-

import os
from scrapy import log
from scrapy.http import Request
from scrapy.contrib.pipeline.images import ImagesPipeline
from woaidu_crawler.utils.select_result import list_first_item

class WoaiduCoverImage(ImagesPipeline):
    """
        this is for download the book covor image and then complete the 
        book_covor_image_path field to the picture's path in the file system.
    """
    def __init__(self, store_uri, download_func=None):
        self.images_store = store_uri
        super(WoaiduCoverImage,self).__init__(store_uri, download_func=None)

    def get_media_requests(self, item, info):
        if item.get('book_covor_image_url'):
            yield Request(item['book_covor_image_url'])

    def item_completed(self, results, item, info):
        if self.LOG_FAILED_RESULTS:
            msg = '%s found errors proessing %s' % (self.__class__.__name__, item)
            for ok, value in results:
                if not ok:
                    log.err(value, msg, spider=info.spider)

        image_paths = [x['path'] for ok, x in results if ok]
        image_path = list_first_item(image_paths)
        item['book_covor_image_path'] = os.path.join(os.path.abspath(self.images_store),image_path) if image_path else ""

        return item

########NEW FILE########
__FILENAME__ = drop_none_download
#!/usr/bin/python
#-*-coding:utf-8-*-

from pprint import pprint
from woaidu_crawler.utils import color
from woaidu_crawler.pipelines.bookfile import NofilesDrop

class DropNoneBookFile(object):
    """
        drop items those book_file and book_file_url are empty. 
    """
    
    Drop_NoneBookFile = True
    
    def __init__(self):
        self.style = color.color_style()

    @classmethod
    def from_crawler(cls, crawler):
        cls.Drop_NoneBookFile = crawler.settings.get('Drop_NoneBookFile',True)
        pipe = cls()
        pipe.crawler = crawler
        return pipe
    
    def process_item(self, item, spider):
        if not item.get('book_file_url',None):
            raise NofilesDrop(item['original_url'])
        
        return item

########NEW FILE########
__FILENAME__ = file
#!/usr/bin/python
#-*-coding:utf-8-*-

import os
import time
import hashlib
import urlparse
import shutil
import urllib
from urlparse import urlparse
from scrapy import log
from twisted.internet import defer
from pprint import pprint 
from woaidu_crawler.utils import color
from scrapy.utils.misc import md5sum
from collections import defaultdict
from scrapy.utils.misc import arg_to_iter
from scrapy.contrib.pipeline.images import MediaPipeline
from woaidu_crawler.utils.select_result import list_first_item
from scrapy.exceptions import NotConfigured, IgnoreRequest

class FileException(Exception):
    """General file error exception"""
    def __init__(self, file_url=None, *args):
        self.file_url = file_url
        self.style = color.color_style()
        Exception.__init__(self, *args)

    def __str__(self):#####for usage: print e
        print self.style.ERROR("ERROR(FileException): %s"%(Exception.__str__(self),))
        
        return Exception.__str__(self)

class FSFilesStore(object):

    def __init__(self, basedir):
        if '://' in basedir:
            basedir = basedir.split('://', 1)[1]
        self.basedir = basedir
        self._mkdir(self.basedir)
        self.created_directories = defaultdict(set)

    def persist_file(self, key, file_content, info, filename):
        self._mkdir(os.path.join(self.basedir, *key.split('/')), info)
        absolute_path = self._get_filesystem_path(key,filename)
        with open(absolute_path,"w") as wf:
            wf.write(file_content)

        with open(absolute_path, 'rb') as file_content:
            checksum = md5sum(file_content)
            
        return checksum

    def stat_file(self, key, info):
        """
            the stat is the file key dir,
            the last_modified is the file that saved to the file key dir.
        """
        
        keydir = os.path.join(self.basedir, *key.split('/'))
        filenames = os.listdir(keydir)
        if len(filenames) != 1:
            shutil.rmtree(keydir,True)
            return {}
        else:
            filename = list_first_item(filenames)
        
        absolute_path = self._get_filesystem_path(key)
        try:
            last_modified = os.path.getmtime(absolute_path)
        except:  # FIXME: catching everything!
            return {}

        with open(os.path.join(absolute_path,filename), 'rb') as file_content:
            checksum = md5sum(file_content)

        return {'last_modified': last_modified, 'checksum': checksum}

    def _get_filesystem_path(self, key,filename=None):
        path_comps = key.split('/')
        if filename:
            path_comps.append(filename)
            return os.path.join(self.basedir, *path_comps)
        else:
            return os.path.join(self.basedir, *path_comps)

    def _mkdir(self, dirname, domain=None):
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        
        #XXX:str.rfind(sub[, start[, end]])
        #Return the highest index in the string where substring sub is found,
        #such that sub is contained within s[start:end]. 
        dirname = dirname[:dirname.rfind('/')] if domain else dirname
        seen = self.created_directories[domain] if domain else set()
        if dirname not in seen:
            seen.add(dirname)

class FilePipeline(MediaPipeline):
    """
        download file pipeline.
    """
    
    MEDIA_NAME = 'file'
    EXPIRES = 90
    URL_GBK_DOMAIN = []
    ATTACHMENT_FILENAME_UTF8_DOMAIN = []
    STORE_SCHEMES = {
        '': FSFilesStore,
        'file': FSFilesStore,
    }
    
    FILE_EXTENTION = ['.doc','.txt','.docx','.rar','.zip','.pdf']
    
    def __init__(self,store_uri,download_func=None):
        if not store_uri:
            raise NotConfigured
        self.store = self._get_store(store_uri)
        self.style = color.color_style()
        super(FilePipeline, self).__init__(download_func=download_func)

    @classmethod
    def from_settings(cls, settings):
        cls.EXPIRES = settings.getint('FILE_EXPIRES', 90)
        cls.ATTACHMENT_FILENAME_UTF8_DOMAIN = settings.get('ATTACHMENT_FILENAME_UTF8_DOMAIN',[])
        cls.URL_GBK_DOMAIN = settings.get('URL_GBK_DOMAIN',[])
        cls.FILE_EXTENTION = settings.get('FILE_EXTENTION',[])
        store_uri = settings['FILE_STORE']
        return cls(store_uri)

    def _get_store(self, uri):
        if os.path.isabs(uri):  # to support win32 paths like: C:\\some\dir
            scheme = 'file'
        else:
            scheme = urlparse.urlparse(uri).scheme

        store_cls = self.STORE_SCHEMES[scheme]
        return store_cls(uri)

    def media_downloaded(self, response, request, info):
        """
            Handler for success downloads.
        """
        
        referer = request.headers.get('Referer')

        if response.status != 200:
            log.msg(format='%(medianame)s (code: %(status)s): Error downloading %(medianame)s from %(request)s referred in <%(referer)s>',
                    level=log.WARNING, spider=info.spider,medianame=self.MEDIA_NAME,
                    status=response.status, request=request, referer=referer)
            raise FileException(request.url,'%s: download-error'%(request.url,))

        if not response.body:
            log.msg(format='%(medianame)s (empty-content): Empty %(medianame)s from %(request)s referred in <%(referer)s>: no-content',
                    level=log.WARNING, spider=info.spider,medianame=self.MEDIA_NAME,
                    request=request, referer=referer)
            raise FileException(request.url,'%s: empty-content'%(request.url,))

        status = 'cached' if 'cached' in response.flags else 'downloaded'
        log.msg(format='%(medianame)s (%(status)s): Downloaded %(medianame)s from %(request)s referred in <%(referer)s>',
                level=log.DEBUG, spider=info.spider,medianame=self.MEDIA_NAME,
                status=status, request=request, referer=referer)

        if self.is_valid_content_type(response):
            raise FileException(request.url,'%s: invalid-content_type'%(request.url,))
        
        filename = self.get_file_name(request,response)
        
        if not filename:
            raise FileException(request.url,'%s: noaccess-filename'%(request.url,))
        
        self.inc_stats(info.spider, status)
        
        try:
            key = self.file_key(request.url)#return the SHA1 hash of the file url
            checksum = self.store.persist_file(key,response.body,info,filename)
        except FileException as exc:
            whyfmt = '%(medianame)s (error): Error processing %(medianame)s from %(request)s referred in <%(referer)s>: %(errormsg)s'
            log.msg(format=whyfmt, level=log.WARNING, spider=info.spider,medianame=self.MEDIA_NAME,
                    request=request, referer=referer, errormsg=str(exc))
            raise
        
        return {'url': request.url, 'path': key, 'checksum': checksum}

    def media_failed(self, failure, request, info):
        if not isinstance(failure.value, IgnoreRequest):
            referer = request.headers.get('Referer')
            log.msg(format='%(medianame)s (unknown-error): Error downloading '
                           '%(medianame)s from %(request)s referred in '
                           '<%(referer)s>: %(exception)s',
                    level=log.WARNING, spider=info.spider, exception=failure.value,
                    medianame=self.MEDIA_NAME, request=request, referer=referer)
        
        raise FileException(request.url,'%s: Error downloading'%(request.url,))

    def media_to_download(self, request, info):
        def _onsuccess(result):
            
            if not result:
                return  # returning None force download

            last_modified = result.get('last_modified', None)
            if not last_modified:
                return  # returning None force download

            age_seconds = time.time() - last_modified
            age_days = age_seconds / 60 / 60 / 24
            if age_days > self.EXPIRES:
                return  # returning None force download

            referer = request.headers.get('Referer')
            log.msg(format='%(medianame)s (uptodate): Downloaded %(medianame)s from %(request)s referred in <%(referer)s>',
                    level=log.DEBUG, spider=info.spider,
                    medianame=self.MEDIA_NAME, request=request, referer=referer)
            self.inc_stats(info.spider, 'uptodate')

            checksum = result.get('checksum', None)
            
            return {'url': request.url, 'path': key, 'checksum': checksum}

        key = self.file_key(request.url)#return the SHA1 hash of the file url
        dfd = defer.maybeDeferred(self.store.stat_file, key, info)
        dfd.addCallbacks(_onsuccess, lambda _: None)
        dfd.addErrback(log.err, self.__class__.__name__ + '.store.stat_file')
        return dfd

    def is_valid_content_type(self,response):
        """
            judge whether is it a valid response by the Content-Type.
        """
        return True

    def inc_stats(self, spider, status):
        spider.crawler.stats.inc_value('%s_file_count'%(self.MEDIA_NAME,) , spider=spider)
        spider.crawler.stats.inc_value('%s_file_status_count/%s' % (self.MEDIA_NAME,status), spider=spider)

    def file_key(self, url):
        """
            return the SHA1 hash of the file url
        """
        
        file_guid = hashlib.sha1(url).hexdigest()
        return '%s/%s' % (urlparse(url).netloc,file_guid)

    def get_file_name(self,request,response):
        """
            Get the raw file name that the sever transfer to.
            
            It examine two places:Content-Disposition,url.
        """
        
        content_dispo = response.headers.get('Content-Disposition','')
        filename = ""
        #print response.headers
        if content_dispo:
            for i in content_dispo.split(';'):
                if "filename" in i:
                    #XXX:use filename= for the specific case that = in the filename
                    filename = i.split('filename=')[1].strip(" \n\'\"")
                    break
        
        if filename:
            #XXX:it the result is:
            #MPLS TE Switching%E6%96%B9%E6%A1%88%E7%99%BD%E7%9A%AE%E4%B9%A6.pdf
            #use urllib.unquote(filename) instead
            if urlparse(request.url).netloc in self.ATTACHMENT_FILENAME_UTF8_DOMAIN:
                filename = filename.decode("utf-8")
            else:
                filename = filename.decode("gbk")
            #print "Content-Disposition:","*"*30,filename
        else:
            guessname = request.url.split('/')[-1]
            #os.path.splitext:
            #Split the pathname path into a pair (root, ext) such that root + ext == path
            if os.path.splitext(guessname)[1].lower() in self.FILE_EXTENTION:
                if urlparse(request.url).netloc in self.URL_GBK_DOMAIN:
                    filename = urllib.unquote(guessname).decode("gbk").encode("utf-8")
                else:
                    filename = urllib.unquote(guessname)
                #print "url:","*"*30,filename
        
        return filename

########NEW FILE########
__FILENAME__ = final_test
#!/usr/bin/python
#-*-coding:utf-8-*-

from pprint import pprint
from woaidu_crawler.utils import color

class FinalTestPipeline(object):
    """
        This only for print the final item for the purpose of debug,because the default
        scrapy output the result,so if you use this pipeline,you better change the scrapy
        source code:
        
        sudo vim /usr/local/lib/python2.7/dist-packages/Scrapy-0.16.4-py2.7.egg/scrapy/core/scrapy.py
        make line 211 like this:
            #log.msg(level=log.DEBUG, spider=spider, **logkws)
    """
    
    def __init__(self):
        self.style = color.color_style()

    @classmethod
    def from_crawler(cls, crawler):
        pipe = cls()
        pipe.crawler = crawler
        return pipe
    
    def process_item(self, item, spider):
        print self.style.NOTICE("SUCCESS(item):" + item['original_url'])
        #pprint(item)
        return item

########NEW FILE########
__FILENAME__ = mongodb
#!/usr/bin/python
#-*-coding:utf-8-*-

import datetime
import traceback
from pprint import pprint
from woaidu_crawler.utils import color
from scrapy import log
from woaidu_crawler.utils import color
from pymongo.connection import MongoClient

class SingleMongodbPipeline(object):
    """
        save the data to mongodb.
    """

    MONGODB_SERVER = "localhost"
    MONGODB_PORT = 27017
    MONGODB_DB = "books_fs"

    def __init__(self):
        """
            The only async framework that PyMongo fully supports is Gevent.
            
            Currently there is no great way to use PyMongo in conjunction with Tornado or Twisted. PyMongo provides built-in connection pooling, so some of the benefits of those frameworks can be achieved just by writing multi-threaded code that shares a MongoClient.
        """
        
        self.style = color.color_style()
        try:
            client = MongoClient(self.MONGODB_SERVER,self.MONGODB_PORT) 
            self.db = client[self.MONGODB_DB]
        except Exception as e:
            print self.style.ERROR("ERROR(SingleMongodbPipeline): %s"%(str(e),))
            traceback.print_exc()

    @classmethod
    def from_crawler(cls, crawler):
        cls.MONGODB_SERVER = crawler.settings.get('SingleMONGODB_SERVER', 'localhost')
        cls.MONGODB_PORT = crawler.settings.getint('SingleMONGODB_PORT', 27017)
        cls.MONGODB_DB = crawler.settings.get('SingleMONGODB_DB', 'books_fs')
        pipe = cls()
        pipe.crawler = crawler
        return pipe

    def process_item(self, item, spider):
        book_detail = {
            'book_name':item.get('book_name'),
            'alias_name':item.get('alias_name',[]),
            'author':item.get('author',[]),
            'book_description':item.get('book_description',''),
            'book_covor_image_path':item.get('book_covor_image_path',''),
            'book_covor_image_url':item.get('book_covor_image_url',''),
            'book_download':item.get('book_download',[]),
            'book_file_url':item.get('book_file_url',''),
            'book_file':item.get('book_file',''),
            'original_url':item.get('original_url',''),
            'update_time':datetime.datetime.utcnow(),
        }
        
        result = self.db['book_detail'].insert(book_detail)
        item["mongodb_id"] = str(result)

        log.msg("Item %s wrote to MongoDB database %s/book_detail" %
                    (result, self.MONGODB_DB),
                    level=log.DEBUG, spider=spider)
        return item

class ShardMongodbPipeline(object):
    """
        save the data to shard mongodb.
    """

    MONGODB_SERVER = "localhost"
    MONGODB_PORT = 27017
    MONGODB_DB = "books_mongo"
    GridFs_Collection = "book_file"

    def __init__(self):
        """
            The only async framework that PyMongo fully supports is Gevent.
            
            Currently there is no great way to use PyMongo in conjunction with Tornado or Twisted. PyMongo provides built-in connection pooling, so some of the benefits of those frameworks can be achieved just by writing multi-threaded code that shares a MongoClient.
        """
        
        self.style = color.color_style()
        try:
            client = MongoClient(self.MONGODB_SERVER,self.MONGODB_PORT) 
            self.db = client[self.MONGODB_DB]
        except Exception as e:
            print self.style.ERROR("ERROR(ShardMongodbPipeline): %s"%(str(e),))
            traceback.print_exc()

    @classmethod
    def from_crawler(cls, crawler):
        cls.MONGODB_SERVER = crawler.settings.get('ShardMONGODB_SERVER', 'localhost')
        cls.MONGODB_PORT = crawler.settings.getint('ShardMONGODB_PORT', 27017)
        cls.MONGODB_DB = crawler.settings.get('ShardMONGODB_DB', 'books_mongo')
        cls.GridFs_Collection = crawler.settings.get('GridFs_Collection', 'book_file')
        pipe = cls()
        pipe.crawler = crawler
        return pipe

    def process_item(self, item, spider):
        book_detail = {
            'book_name':item.get('book_name'),
            'alias_name':item.get('alias_name',[]),
            'author':item.get('author',[]),
            'book_description':item.get('book_description',''),
            'book_covor_image_path':item.get('book_covor_image_path',''),
            'book_covor_image_url':item.get('book_covor_image_url',''),
            'book_download':item.get('book_download',[]),
            'book_file_url':item.get('book_file_url',''),
            'book_file_id':item.get('book_file_id',''),
            'original_url':item.get('original_url',''),
            'update_time':datetime.datetime.utcnow(),
        }
        
        result = self.db['book_detail'].insert(book_detail)
        item["mongodb_id"] = str(result)

        log.msg("Item %s wrote to MongoDB database %s/book_detail" %
                    (result, self.MONGODB_DB),
                    level=log.DEBUG, spider=spider)
        return item

########NEW FILE########
__FILENAME__ = mongodb_book_file
#!/usr/bin/python
#-*-coding:utf-8-*-

import os
import itertools
import gridfs
import hashlib
import urlparse
import traceback
import datetime
from scrapy import log
from scrapy.item import Item
from urlparse import urlparse
from pprint import pprint
from twisted.internet import defer
from scrapy.http import Request
from woaidu_crawler.utils import color
from scrapy.utils.misc import arg_to_iter
from pymongo import MongoClient
from twisted.internet.defer import Deferred, DeferredList
from woaidu_crawler.utils.select_result import list_first_item
from woaidu_crawler.pipelines.file import FilePipeline,FSFilesStore,FileException
from scrapy.exceptions import DropItem, NotConfigured

class NofilesDrop(DropItem):
    """Product with no files exception"""
    def __init__(self, original_url="", *args):
        self.original_url = original_url
        self.style = color.color_style()
        DropItem.__init__(self, *args)

    def __str__(self):#####for usage: print e
        print self.style.ERROR("DROP(NofilesDrop):" + self.original_url)

        return DropItem.__str__(self)

class BookFileException(FileException):
    """General book file error exception"""

class MongodbBookFilesStore(FSFilesStore):
    """
        save book file to gridfs of mongodb.
    """

    ShardMONGODB_SERVER = "localhost"
    ShardMONGODB_PORT = 27017
    ShardMONGODB_DB = "books_mongo"
    GridFs_Collection = "book_file"

    def __init__(self, shard_server,shard_port,shard_db,shard_gridfs_collection):
        self.style = color.color_style()
        try:
            client = MongoClient(shard_server,shard_port)
            self.db = client[shard_db]
            self.fs = gridfs.GridFS(self.db,shard_gridfs_collection)
        except Exception as e:
            print self.style.ERROR("ERROR(MongodbBookFilesStore): %s"%(str(e),))
            traceback.print_exc()
    
    def persist_file(self, key, file_content, info, filename):
        contentType = os.path.splitext(filename)[1][1:].lower()
        
        book_file_id = self.fs.put(file_content,_id=key,filename=filename,contentType=contentType)
        checksum = self.fs.get(book_file_id).md5
            
        return (book_file_id,checksum)

    def stat_file(self, key, info):
        """
            the stat is the file key dir,
            the last_modified is the file that saved to the file key dir.
        """
        checksum = self.fs.get(key).md5
        last_modified = self.fs.get(key).upload_date

        return {'last_modified': last_modified, 'checksum': checksum}

class MongodbWoaiduBookFile(FilePipeline):
    """
        This is for download the book file and then define the book_file_id 
        field to the file's gridfs id in the mongodb.
    """

    MEDIA_NAME = 'mongodb_bookfile'
    EXPIRES = 90
    BOOK_FILE_CONTENT_TYPE = []
    URL_GBK_DOMAIN = []
    ATTACHMENT_FILENAME_UTF8_DOMAIN = []
    STORE_SCHEMES = {
        '': MongodbBookFilesStore,
        'mongodb': MongodbBookFilesStore,
    }
    
    FILE_EXTENTION = ['.doc','.txt','.docx','.rar','.zip','.pdf']

    def __init__(self,shard_server,shard_port,shard_db,shard_gridfs_collection,download_func=None):
        self.style = color.color_style()
        ##########from MediaPipeline###########
        self.spiderinfo = {}
        self.download_func = download_func
        ##########from MediaPipeline###########

        self.store = self._get_store(shard_server,shard_port,shard_db,shard_gridfs_collection)
        self.item_download = {}

    @classmethod
    def from_settings(cls, settings):
        cls.EXPIRES = settings.getint('BOOK_FILE_EXPIRES', 90)
        cls.BOOK_FILE_CONTENT_TYPE = settings.get('BOOK_FILE_CONTENT_TYPE',[])
        cls.ATTACHMENT_FILENAME_UTF8_DOMAIN = settings.get('ATTACHMENT_FILENAME_UTF8_DOMAIN',[])
        cls.URL_GBK_DOMAIN = settings.get('URL_GBK_DOMAIN',[])
        cls.FILE_EXTENTION = settings.get('FILE_EXTENTION',[])
        shard_server = settings.get('ShardMONGODB_SERVER',"localhost")
        shard_port = settings.get('ShardMONGODB_PORT',27017)
        shard_db = settings.get('ShardMONGODB_DB',"books_mongo")
        shard_gridfs_collection = settings.get('GridFs_Collection','book_file')
        return cls(shard_server,shard_port,shard_db,shard_gridfs_collection)

    def _get_store(self, shard_server,shard_port,shard_db,shard_gridfs_collection):
        scheme = 'mongodb'

        store_cls = self.STORE_SCHEMES[scheme]
        return store_cls(shard_server,shard_port,shard_db,shard_gridfs_collection)

    def process_item(self, item, spider):
        """
            custom process_item func,so it will manage the Request result.
        """
        
        info = self.spiderinfo[spider]
        requests = arg_to_iter(self.get_media_requests(item, info))
        dlist = [self._process_request(r, info) for r in requests]
        dfd = DeferredList(dlist, consumeErrors=1)
        dfd.addCallback(self.item_completed, item, info)
        return dfd.addCallback(self.another_process_item, item, info)

    def another_process_item(self, result, item, info):
        """
            custom process_item func,so it will manage the Request result.
        """
        
        assert isinstance(result, (Item, Request)), \
                    "WoaiduBookFile pipeline' item_completed must return Item or Request, got %s" % \
                    (type(result))
        if isinstance(result,Item):
            return result
        elif isinstance(result,Request):
            dlist = [self._process_request(r, info) for r in arg_to_iter(result)]
            dfd = DeferredList(dlist, consumeErrors=1)
            dfd.addCallback(self.item_completed, item, info)
            #XXX:This will cause one item maybe return many times,it depends on how many 
            #times the download url failed.But it doesn't matter.Because when raise errors,
            #the items are no longer processed by further pipeline components.And when all
            #url download failed we can drop that item which book_file or book_file_url are
            #empty.
            return dfd.addCallback(self.another_process_item, item, info)
        else:
            raise NofilesDrop

    def get_media_requests(self, item, info):
        """
            Only download once per book,so it pick out one from all of the download urls.
        """ 

        #XXX:To test specific url,you can use the following method:
        #return Request("http://down.wmtxt.com/wmtxt/wmtxt/UploadFile/2010-6/%A1%B6%D3%F6%BC%FB%C4%E3%A1%B7.rar")
        if item.get('book_download'):
            downloadfile_urls = [i['url'] for i in item.get('book_download') if i['url']]
            downloadfile_urls = list(set(itertools.chain(*downloadfile_urls)))
            first_download_file = list_first_item(downloadfile_urls)
            self.item_download[item['original_url']] = downloadfile_urls[1:]
            if first_download_file:
                return Request(first_download_file)

    def media_downloaded(self, response, request, info):
        """
            Handler for success downloads.
        """
        
        referer = request.headers.get('Referer')

        if response.status != 200:
            log.msg(format='%(medianame)s (code: %(status)s): Error downloading %(medianame)s from %(request)s referred in <%(referer)s>',
                    level=log.WARNING, spider=info.spider,medianame=self.MEDIA_NAME,
                    status=response.status, request=request, referer=referer)
            raise BookFileException(request.url,'%s: download-error'%(request.url,))

        if not response.body:
            log.msg(format='%(medianame)s (empty-content): Empty %(medianame)s from %(request)s referred in <%(referer)s>: no-content',
                    level=log.WARNING, spider=info.spider,medianame=self.MEDIA_NAME,
                    request=request, referer=referer)
            raise BookFileException(request.url,'%s: empty-content'%(request.url,))

        status = 'cached' if 'cached' in response.flags else 'downloaded'
        log.msg(format='%(medianame)s (%(status)s): Downloaded %(medianame)s from %(request)s referred in <%(referer)s>',
                level=log.DEBUG, spider=info.spider,medianame=self.MEDIA_NAME,
                status=status, request=request, referer=referer)

        if self.is_valid_content_type(response):
            raise BookFileException(request.url,'%s: invalid-content_type'%(request.url,))
        
        filename = self.get_file_name(request,response)
        
        if not filename:
            raise BookFileException(request.url,'%s: noaccess-filename'%(request.url,))
        
        self.inc_stats(info.spider, status)
        
        try:
            key = self.file_key(request.url)#return the SHA1 hash of the file url
            book_file_id,checksum = self.store.persist_file(key,response.body,info,filename)
        except BookFileException as exc:
            whyfmt = '%(medianame)s (error): Error processing %(medianame)s from %(request)s referred in <%(referer)s>: %(errormsg)s'
            log.msg(format=whyfmt, level=log.WARNING, spider=info.spider,medianame=self.MEDIA_NAME,
                    request=request, referer=referer, errormsg=str(exc))
            raise
        
        return {'url': request.url, 'book_file_id': book_file_id, 'checksum': checksum}

    def media_to_download(self, request, info):
        def _onsuccess(result):
            
            if not result:
                return  # returning None force download

            last_modified = result.get('last_modified', None)
            if not last_modified:
                return  # returning None force download

            timedelta_obj = datetime.datetime.now() - last_modified
            age_seconds = timedelta_obj.total_seconds()
            age_days = age_seconds / 60 / 60 / 24
            if age_days > self.EXPIRES:
                return  # returning None force download

            referer = request.headers.get('Referer')
            log.msg(format='%(medianame)s (uptodate): Downloaded %(medianame)s from %(request)s referred in <%(referer)s>',
                    level=log.DEBUG, spider=info.spider,
                    medianame=self.MEDIA_NAME, request=request, referer=referer)
            self.inc_stats(info.spider, 'uptodate')

            checksum = result.get('checksum', None)
            
            return {'url': request.url, 'book_file_id': key, 'checksum': checksum}

        key = self.file_key(request.url)#return the SHA1 hash of the file url
        dfd = defer.maybeDeferred(self.store.stat_file, key, info)
        dfd.addCallbacks(_onsuccess, lambda _: None)
        dfd.addErrback(log.err, self.__class__.__name__ + '.store.stat_file')
        return dfd

    def file_key(self, url):
        """
            return the SHA1 hash of the file url
        """
        
        file_guid = hashlib.sha1(url).hexdigest()
        return '%s_%s' % (urlparse(url).netloc,file_guid)

    def item_completed(self, results, item, info):
        if self.LOG_FAILED_RESULTS:
            msg = '%s found errors proessing %s' % (self.__class__.__name__, item)
            for ok, value in results:
                if not ok:
                    log.err(value, msg, spider=info.spider)

        bookfile_ids_urls = [(x['book_file_id'],x['url']) for ok, x in results if ok]
        bookfile_id_url = list_first_item(bookfile_ids_urls)
        if bookfile_id_url:
            item['book_file_id'] = bookfile_id_url[0]
            item['book_file_url'] = bookfile_id_url[1]
            return item
        else:
            if self.item_download[item['original_url']]:
                next = list_first_item(self.item_download[item['original_url']])
                self.item_download[item['original_url']] = self.item_download[item['original_url']][1:]
                return Request(next)
            else:
                return item

    def is_valid_content_type(self,response):
        """
            judge whether is it a valid response by the Content-Type.
        """
        content_type = response.headers.get('Content-Type','')
        
        return content_type not in self.BOOK_FILE_CONTENT_TYPE

########NEW FILE########
__FILENAME__ = dupefilter
#!/usr/bin/python
#-*-coding:utf-8-*-

import redis
import time

from scrapy.dupefilter import BaseDupeFilter
from scrapy.utils.request import request_fingerprint


class RFPDupeFilter(BaseDupeFilter):
    """Redis-based request duplication filter"""

    def __init__(self, server, key):
        """Initialize duplication filter

        Parameters
        ----------
        server : Redis instance
        key : str
            Where to store fingerprints
        """
        self.server = server
        self.key = key

    @classmethod
    def from_settings(cls, settings):
        host = settings.get('REDIS_HOST', 'localhost')
        port = settings.get('REDIS_PORT', 6379)
        server = redis.Redis(host, port)
        # create one-time key. needed to support to use this
        # class as standalone dupefilter with scrapy's default scheduler
        # if scrapy passes spider on open() method this wouldn't be needed
        key = "dupefilter:%s" % int(time.time())
        return cls(server, key)

    @classmethod
    def from_crawler(cls, crawler):
        return cls.from_settings(crawler.settings)

    def request_seen(self, request):
        """
            use sismember judge whether fp is duplicate.
        """
        
        fp = request_fingerprint(request)
        if self.server.sismember(self.key,fp):
            return True
        self.server.sadd(self.key, fp)
        return False

    def close(self, reason):
        """Delete data on close. Called by scrapy's scheduler"""
        self.clear()

    def clear(self):
        """Clears fingerprints data"""
        self.server.delete(self.key)

########NEW FILE########
__FILENAME__ = queue
#!/usr/bin/python
#-*-coding:utf-8-*-

from scrapy.utils.reqser import request_to_dict, request_from_dict

try:
    import cPickle as pickle
except ImportError:
    import pickle


class Base(object):
    """Per-spider queue/stack base class"""

    def __init__(self, server, spider, key):
        """Initialize per-spider redis queue.

        Parameters:
            server -- redis connection
            spider -- spider instance
            key -- key for this queue (e.g. "%(spider)s:queue")
        """
        self.server = server
        self.spider = spider
        self.key = key % {'spider': spider.name}

    def _encode_request(self, request):
        """Encode a request object"""
        return pickle.dumps(request_to_dict(request, self.spider), protocol=-1)

    def _decode_request(self, encoded_request):
        """Decode an request previously encoded"""
        return request_from_dict(pickle.loads(encoded_request), self.spider)

    def __len__(self):
        """Return the length of the queue"""
        raise NotImplementedError

    def push(self, request):
        """Push a request"""
        raise NotImplementedError

    def pop(self):
        """Pop a request"""
        raise NotImplementedError

    def clear(self):
        """Clear queue/stack"""
        self.server.delete(self.key)


class SpiderQueue(Base):
    """Per-spider FIFO queue"""

    def __len__(self):
        """Return the length of the queue"""
        return self.server.llen(self.key)

    def push(self, request):
        """Push a request"""
        self.server.lpush(self.key, self._encode_request(request))

    def pop(self):
        """Pop a request"""
        data = self.server.rpop(self.key)
        if data:
            return self._decode_request(data)


class SpiderPriorityQueue(Base):
    """Per-spider priority queue abstraction using redis' sorted set"""

    def __len__(self):
        """Return the length of the queue"""
        return self.server.zcard(self.key)

    def push(self, request):
        """Push a request"""
        data = self._encode_request(request)
        pairs = {data:-request.priority}
        self.server.zadd(self.key, **pairs)

    def pop(self):
        """Pop a request"""
        # use atomic range/remove using multi/exec
        pipe = self.server.pipeline()
        pipe.multi()
        pipe.zrange(self.key, 0, 0).zremrangebyrank(self.key, 0, 0)
        results, count = pipe.execute()
        if results:
            return self._decode_request(results[0])


class SpiderStack(Base):
    """Per-spider stack"""

    def __len__(self):
        """Return the length of the stack"""
        return self.server.llen(self.key)

    def push(self, request):
        """Push a request"""
        self.server.lpush(self.key, self._encode_request(request))

    def pop(self):
        """Pop a request"""
        data = self.server.lpop(self.key)
        if data:
            return self._decode_request(data)


__all__ = ['SpiderQueue', 'SpiderPriorityQueue', 'SpiderStack']

########NEW FILE########
__FILENAME__ = scheduler
#!/usr/bin/python
#-*-coding:utf-8-*-

import redis
from scrapy.utils.misc import load_object
from .dupefilter import RFPDupeFilter


# default values
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
SCHEDULER_PERSIST = False
QUEUE_KEY = '%(spider)s:requests'
QUEUE_CLASS = '.queue.SpiderPriorityQueue'
DUPEFILTER_KEY = '%(spider)s:dupefilter'


class Scheduler(object):
    """Redis-based scheduler"""

    def __init__(self, server, persist, queue_key, queue_cls, dupefilter_key):
        """Initialize scheduler.

        Parameters
        ----------
        server : Redis instance
        persist : bool
        queue_key : str
        queue_cls : queue class
        dupefilter_key : str
        """
        self.server = server
        self.persist = persist
        self.queue_key = queue_key
        self.queue_cls = queue_cls
        self.dupefilter_key = dupefilter_key

    def __len__(self):
        return len(self.queue)

    @classmethod
    def from_settings(cls, settings):
        host = settings.get('REDIS_HOST', REDIS_HOST)
        port = settings.get('REDIS_PORT', REDIS_PORT)
        persist = settings.get('SCHEDULER_PERSIST', SCHEDULER_PERSIST)
        queue_key = settings.get('SCHEDULER_QUEUE_KEY', QUEUE_KEY)
        queue_cls = load_object(settings.get('SCHEDULER_QUEUE_CLASS', QUEUE_CLASS))
        dupefilter_key = settings.get('DUPEFILTER_KEY', DUPEFILTER_KEY)
        server = redis.Redis(host, port)
        return cls(server, persist, queue_key, queue_cls, dupefilter_key)

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        cls.stats = crawler.stats
        return cls.from_settings(settings)

    def open(self, spider):
        """
            execute this function when open one spider
        """
        
        self.spider = spider
        self.queue = self.queue_cls(self.server, spider, self.queue_key)
        self.df = RFPDupeFilter(self.server, self.dupefilter_key % {'spider': spider.name})
        # notice if there are requests already in the queue to resume the crawl
        if len(self.queue):
            spider.log("Resuming crawl (%d requests scheduled)" % len(self.queue))

    def close(self, reason):
        if not self.persist:
            self.df.clear()
            self.queue.clear()

    def enqueue_request(self, request):
        if not request.dont_filter and self.df.request_seen(request):
            return
        self.stats.inc_value('scheduler/enqueued/redis', spider=self.spider)
        self.queue.push(request)

    def next_request(self):
        request = self.queue.pop()
        if request:
            self.stats.inc_value('scheduler/dequeued/redis', spider=self.spider)
        return request

    def has_pending_requests(self):
        return len(self) > 0

########NEW FILE########
__FILENAME__ = settings
#!/usr/bin/python
#-*-coding:utf-8-*-

# Scrapy settings for woaidu_crawler project
import os

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))

BOT_NAME = 'woaidu_crawler'

SPIDER_MODULES = ['woaidu_crawler.spiders']
NEWSPIDER_MODULE = 'woaidu_crawler.spiders'

DOWNLOAD_DELAY = 1
CONCURRENT_ITEMS = 100
CONCURRENT_REQUESTS = 16
#The maximum number of concurrent (ie. simultaneous) requests that will be performed to any single domain.
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 0
DEPTH_LIMIT = 0
DEPTH_PRIORITY = 0
DNSCACHE_ENABLED = True
#DUPEFILTER_CLASS = 'scrapy.dupefilter.RFPDupeFilter'
#SCHEDULER = 'scrapy.core.scheduler.Scheduler'

#AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3.0
AUTOTHROTTLE_CONCURRENCY_CHECK_PERIOD = 10#How many responses should pass to perform concurrency adjustments.

#XXX:scrapy's item pipelines have orders!!!!!,it will go through all the pipelines by the order of the list;
#So if you change the item and return it,the new item will transfer to the next pipeline.
#XXX:notice:
#if you want to use shard mongodb,you need MongodbWoaiduBookFile and ShardMongodbPipeline
#if you want to use single mongodb,you need WoaiduBookFile and SingleMongodbPipeline
ITEM_PIPELINES = ['woaidu_crawler.pipelines.cover_image.WoaiduCoverImage',
#    'woaidu_crawler.pipelines.bookfile.WoaiduBookFile',
    'woaidu_crawler.pipelines.mongodb_book_file.MongodbWoaiduBookFile',
    'woaidu_crawler.pipelines.drop_none_download.DropNoneBookFile',
#    'woaidu_crawler.pipelines.mongodb.SingleMongodbPipeline',
    'woaidu_crawler.pipelines.mongodb.ShardMongodbPipeline',
    'woaidu_crawler.pipelines.final_test.FinalTestPipeline',]
#ITEM_PIPELINES = ['woaidu_crawler.pipelines.WoaiduBookFile',]

IMAGES_STORE = os.path.join(PROJECT_DIR,'media/book_covor_image')
IMAGES_EXPIRES = 30
IMAGES_THUMBS = {
     'small': (50, 50),
     'big': (270, 270),
}

IMAGES_MIN_HEIGHT = 0
IMAGES_MIN_WIDTH = 0

COOKIES_ENABLED = False

#USER_AGENT = 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31'

DOWNLOADER_MIDDLEWARES = {
#    'woaidu_crawler.contrib.downloadmiddleware.google_cache.GoogleCacheMiddleware':50,
    'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
    'woaidu_crawler.contrib.downloadmiddleware.rotate_useragent.RotateUserAgentMiddleware':400,
}

#GOOGLE_CACHE_DOMAINS = ['www.woaidu.org',]

#To make RotateUserAgentMiddleware enable.
USER_AGENT = ''

FILE_EXPIRES = 30
BOOK_FILE_EXPIRES = 30
FILE_STORE = os.path.join(PROJECT_DIR,'media/files')
BOOK_FILE_STORE = os.path.join(PROJECT_DIR,'media/book_files')

#For more mime types about file,you can visit:
#http://mimeapplication.net/
BOOK_FILE_CONTENT_TYPE = ['application/file',
    'application/zip',
    'application/octet-stream',
    'application/x-zip-compressed',
    'application/x-octet-stream',
    'application/gzip',
    'application/pdf',
    'application/ogg',
    'application/vnd.oasis.opendocument.text',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/x-dvi',
    'application/x-rar-compressed',
    'application/x-tar',
    'multipart/x-zip',
    'application/x-zip',
    'application/x-winzip',
    'application/x-compress',
    'application/x-compressed',
    'application/x-gzip',
    'zz-application/zz-winassoc-arj',
    'application/x-stuffit',
    'application/arj',
    'application/x-arj',
    'multipart/x-tar',
    'text/plain',]

URL_GBK_DOMAIN = ['www.paofuu.com',
        'down.wmtxt.com',
        'www.txt163.com',
        'down.txt163.com',
        'down.sjtxt.com:8199',
        'file.txtbook.com.cn',
        'www.yyytxt.com',
        'www.27xs.org',
        'down.dusuu.com:8199',
        'down.txtqb.cn']
ATTACHMENT_FILENAME_UTF8_DOMAIN = []

FILE_EXTENTION = ['.doc','.txt','.docx','.rar','.zip','.pdf']

Drop_NoneBookFile = True

LOG_FILE = "logs/scrapy.log"

STATS_CLASS = 'woaidu_crawler.statscol.graphite.RedisGraphiteStatsCollector'

GRAPHITE_HOST = '127.0.0.1'
GRAPHITE_PORT = 2003
GRAPHITE_IGNOREKEYS = []

SingleMONGODB_SERVER = "localhost"
SingleMONGODB_PORT = 27017
SingleMONGODB_DB = "books_fs"

ShardMONGODB_SERVER = "localhost"
ShardMONGODB_PORT = 27017
ShardMONGODB_DB = "books_mongo"
GridFs_Collection = "book_file"

SCHEDULER = "woaidu_crawler.scrapy_redis.scheduler.Scheduler"
SCHEDULER_PERSIST = False
SCHEDULER_QUEUE_CLASS = 'woaidu_crawler.scrapy_redis.queue.SpiderPriorityQueue'

########NEW FILE########
__FILENAME__ = woaidu_detail_spider
#!/usr/bin/python
#-*-coding:utf-8-*-

import time
from pprint import pprint
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from woaidu_crawler.items import WoaiduCrawlerItem
from woaidu_crawler.utils.select_result import list_first_item,strip_null,deduplication,clean_url

class WoaiduSpider(BaseSpider):
    name = "woaidu"
    start_urls = (
            'http://www.woaidu.org/sitemap_1.html',
    )

    def parse(self,response):
        response_selector = HtmlXPathSelector(response)
        next_link = list_first_item(response_selector.select(u'//div[@class="k2"]/div/a[text()="下一页"]/@href').extract())
        if next_link:
            next_link = clean_url(response.url,next_link,response.encoding)
            yield Request(url=next_link, callback=self.parse)

        for detail_link in response_selector.select(u'//div[contains(@class,"sousuolist")]/a/@href').extract():
            if detail_link:
                detail_link = clean_url(response.url,detail_link,response.encoding)
                yield Request(url=detail_link, callback=self.parse_detail)

    def parse_detail(self, response):
        woaidu_item = WoaiduCrawlerItem()

        response_selector = HtmlXPathSelector(response)
        woaidu_item['book_name'] = list_first_item(response_selector.select('//div[@class="zizida"][1]/text()').extract())
        woaidu_item['author'] = [list_first_item(response_selector.select('//div[@class="xiaoxiao"][1]/text()').extract())[5:].strip(),]
        woaidu_item['book_description'] = list_first_item(response_selector.select('//div[@class="lili"][1]/text()').extract()).strip()
        woaidu_item['book_covor_image_url'] = list_first_item(response_selector.select('//div[@class="hong"][1]/img/@src').extract())

        download = []
        for i in response_selector.select('//div[contains(@class,"xiazai_xiao")]')[1:]:
            download_item = {}
            download_item['url'] = \
                strip_null( \
                    deduplication(\
                        [\
                            list_first_item(i.select('./div')[0].select('./a/@href').extract()),\
                            list_first_item(i.select('./div')[1].select('./a/@href').extract())\
                        ]\
                    )\
                )
            
            download_item['progress'] = list_first_item(i.select('./div')[2].select('./text()').extract())
            download_item['update_time'] = list_first_item(i.select('./div')[3].select('./text()').extract())
            download_item['source_site'] = \
                    [\
                        list_first_item(i.select('./div')[4].select('./a/text()').extract()),\
                        list_first_item(i.select('./div')[4].select('./a/@href').extract())\
                    ]\

            download.append(download_item)

        woaidu_item['book_download'] = download
        woaidu_item['original_url'] = response.url
        
        yield woaidu_item

########NEW FILE########
__FILENAME__ = graphite
#!/usr/bin/python
#-*-coding:utf-8-*-

import redis
import pprint
from scrapy import log
from socket import socket
from time import time
from woaidu_crawler.utils import color
from scrapy.statscol import StatsCollector

# default values
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
STATS_KEY = 'scrapy:stats'

class GraphiteClient(object):
    """
        The client thats send data to graphite.
        
        Can have some ideas from /opt/graphite/examples/example-client.py
    """
    
    def __init__(self, host="127.0.0.1", port=2003):
        self.style = color.color_style()
        self._sock = socket()
        self._sock.connect((host,port))

    def send(self, metric, value, timestamp=None):
        try:
            self._sock.send("%s %g %s\n\n" % (metric, value, timestamp or int(time())))
        except Exception as err:
            self.style.ERROR("SocketError(GraphiteClient): " + str(err))

class GraphiteStatsCollector(StatsCollector):
    """
        send the stats data to graphite.
        
        The idea is from Julien Duponchelle,The url:https://github.com/noplay/scrapy-graphite
        
        How to use this:
            1.install graphite and configure it.For more infomation about graphite you can visit
        http://graphite.readthedocs.org/en/0.9.10/ and http://graphite.wikidot.com.
            2.edit /opt/graphite/webapp/content/js/composer_widgets.js,locate the ‘interval’
        variable inside toggleAutoRefresh function,Change its value from ’60′ to ’1′.
            3.add this in storage-aggregation.conf:
                [scrapy_min]
                pattern = ^scrapy\..*_min$
                xFilesFactor = 0.1
                aggregationMethod = min

                [scrapy_max]
                pattern = ^scrapy\..*_max$
                xFilesFactor = 0.1
                aggregationMethod = max

                [scrapy_sum]
                pattern = ^scrapy\..*_count$
                xFilesFactor = 0.1
                aggregationMethod = sum
            4.in settings set:
                STATS_CLASS = 'scrapygraphite.GraphiteStatsCollector'
                GRAPHITE_HOST = '127.0.0.1'
                GRAPHITE_PORT = 2003
                
        The screenshot in woaidu_crawler/screenshots/graphite
    """

    GRAPHITE_HOST = '127.0.0.1'
    GRAPHITE_PORT = 2003
    GRAPHITE_IGNOREKEYS = []#to ignore it,prevent to send data to graphite
    
    def __init__(self, crawler):
        super(GraphiteStatsCollector, self).__init__(crawler)

        host = crawler.settings.get("GRAPHITE_HOST", self.GRAPHITE_HOST)
        port = crawler.settings.get("GRAPHITE_PORT", self.GRAPHITE_PORT)
        self.ignore_keys = crawler.settings.get("GRAPHITE_IGNOREKEYS",self.GRAPHITE_IGNOREKEYS)
        self._graphiteclient = GraphiteClient(host,port)

    def _get_stats_key(self, spider, key):
        if spider is not None:
            return "scrapy.spider.%s.%s" % (spider.name, key)
        return "scrapy.%s" % (key)

    def set_value(self, key, value, spider=None):
        super(GraphiteStatsCollector, self).set_value(key, value, spider)
        self._set_value(key, value, spider)

    def _set_value(self, key, value, spider):
        if isinstance(value, (int, float)) and key not in self.ignore_keys:
            k = self._get_stats_key(spider, key)
            self._graphiteclient.send(k, value)

    def inc_value(self, key, count=1, start=0, spider=None):
        super(GraphiteStatsCollector, self).inc_value(key, count, start, spider)
        self._graphiteclient.send(self._get_stats_key(spider, key),self.get_value(key))

    def max_value(self, key, value, spider=None):
        super(GraphiteStatsCollector, self).max_value(key, value, spider)
        self._graphiteclient.send(self._get_stats_key(spider, key),self.get_value(key))

    def min_value(self, key, value, spider=None):
        super(GraphiteStatsCollector, self).min_value(key, value, spider)
        self._graphiteclient.send(self._get_stats_key(spider, key),self.get_value(key))

    def set_stats(self, stats, spider=None):
        super(GraphiteStatsCollector, self).set_stats(stats, spider)
        for key in stats:
            self._set_value(key, stats[key], spider)

class RedisStatsCollector(object):
    """
        Save stats data in redis for distribute situation.
    """
    
    def __init__(self, crawler):
        self._dump = crawler.settings.getbool('STATS_DUMP')#default: STATS_DUMP = True
        host = crawler.settings.get('REDIS_HOST', REDIS_HOST)
        port = crawler.settings.get('REDIS_PORT', REDIS_PORT)
        self.stats_key = crawler.settings.get('STATS_KEY', STATS_KEY)
        self.server = redis.Redis(host, port)
        
    def get_value(self, key, default=None, spider=None):
        if self.server.hexists(self.stats_key,key):
            return int(self.server.hget(self.stats_key,key))
        else:
            return default

    def get_stats(self, spider=None):
        return self.server.hgetall(self.stats_key)

    def set_value(self, key, value, spider=None):
        self.server.hset(self.stats_key,key,value)

    def set_stats(self, stats, spider=None):
        self.server.hmset(self.stats_key,stats)

    def inc_value(self, key, count=1, start=0, spider=None):
        if not self.server.hexists(self.stats_key,key):
            self.set_value(key, start)
        self.server.hincrby(self.stats_key,key,count)

    def max_value(self, key, value, spider=None):
        self.set_value(key, max(self.get_value(key,value),value))

    def min_value(self, key, value, spider=None):
        self.set_value(key, min(self.get_value(key,value),value))

    def clear_stats(self, spider=None):
        self.server.delete(self.stats_key)

    def open_spider(self, spider):
        pass

    def close_spider(self, spider, reason):
        if self._dump:
            log.msg("Dumping Scrapy stats:\n" + pprint.pformat(self.get_stats()), \
                spider=spider)
        self._persist_stats(self.get_stats(), spider)

    def _persist_stats(self, stats, spider):
        pass
        
class RedisGraphiteStatsCollector(RedisStatsCollector):
    """
        send the stats data to graphite and save stats data in redis for distribute situation.
        
        The idea is from Julien Duponchelle,The url:https://github.com/noplay/scrapy-graphite
        
        How to use this:
            1.install graphite and configure it.For more infomation about graphite you can visit
        http://graphite.readthedocs.org/en/0.9.10/ and http://graphite.wikidot.com.
            2.edit /opt/graphite/webapp/content/js/composer_widgets.js,locate the ‘interval’
        variable inside toggleAutoRefresh function,Change its value from ’60′ to ’1′.
            3.add this in storage-aggregation.conf:
                [scrapy_min]
                pattern = ^scrapy\..*_min$
                xFilesFactor = 0.1
                aggregationMethod = min

                [scrapy_max]
                pattern = ^scrapy\..*_max$
                xFilesFactor = 0.1
                aggregationMethod = max

                [scrapy_sum]
                pattern = ^scrapy\..*_count$
                xFilesFactor = 0.1
                aggregationMethod = sum
            4.in settings set:
                STATS_CLASS = 'scrapygraphite.RedisGraphiteStatsCollector'
                GRAPHITE_HOST = '127.0.0.1'
                GRAPHITE_PORT = 2003
                
        The screenshot in woaidu_crawler/screenshots/graphite
    """

    GRAPHITE_HOST = '127.0.0.1'
    GRAPHITE_PORT = 2003
    GRAPHITE_IGNOREKEYS = []#to ignore it,prevent to send data to graphite
    
    def __init__(self, crawler):
        super(RedisGraphiteStatsCollector, self).__init__(crawler)

        host = crawler.settings.get("GRAPHITE_HOST", self.GRAPHITE_HOST)
        port = crawler.settings.get("GRAPHITE_PORT", self.GRAPHITE_PORT)
        self.ignore_keys = crawler.settings.get("GRAPHITE_IGNOREKEYS",self.GRAPHITE_IGNOREKEYS)
        self._graphiteclient = GraphiteClient(host,port)

    def _get_stats_key(self, spider, key):
        if spider is not None:
            return "scrapy.spider.%s.%s" % (spider.name, key)
        return "scrapy.%s" % (key)

    def set_value(self, key, value, spider=None):
        super(RedisGraphiteStatsCollector, self).set_value(key, value, spider)
        self._set_value(key, value, spider)

    def _set_value(self, key, value, spider):
        if isinstance(value, (int, float)) and key not in self.ignore_keys:
            k = self._get_stats_key(spider, key)
            self._graphiteclient.send(k, value)

    def inc_value(self, key, count=1, start=0, spider=None):
        super(RedisGraphiteStatsCollector, self).inc_value(key, count, start, spider)
        self._graphiteclient.send(self._get_stats_key(spider, key),self.get_value(key))

    def max_value(self, key, value, spider=None):
        super(RedisGraphiteStatsCollector, self).max_value(key, value, spider)
        self._graphiteclient.send(self._get_stats_key(spider, key),self.get_value(key))

    def min_value(self, key, value, spider=None):
        super(RedisGraphiteStatsCollector, self).min_value(key, value, spider)
        self._graphiteclient.send(self._get_stats_key(spider, key),self.get_value(key))

    def set_stats(self, stats, spider=None):
        super(RedisGraphiteStatsCollector, self).set_stats(stats, spider)
        for key in stats:
            self._set_value(key, stats[key], spider)

########NEW FILE########
__FILENAME__ = color
#!/usr/bin/python
#-*- coding:utf-8 -*-
"""
    Sets up the terminal color scheme.
"""

import os
import sys

from woaidu_crawler.utils import termcolors

def supports_color():
    """
    Returns True if the running system's terminal supports color, and False
    otherwise.
    """
    unsupported_platform = (sys.platform in ('win32', 'Pocket PC'))
    # isatty is not always implemented, #6223.
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    #sys.stdout:File objects corresponding to the interpreter’s standard output,
    #isatty():判断file obj是否链接到了一个tty(终端)设备上
    if unsupported_platform or not is_a_tty:
        return False
    return True

def color_style():
    """Returns a Style object with the  color scheme."""
    if not supports_color():
        style = no_style()
    else:
        SPIDER_COLORS = os.environ.get('SPIDER_COLORS', '')
        #返回默认的palette,DARK_PALETTE
        color_settings = termcolors.parse_color_setting(SPIDER_COLORS)
        if color_settings:
            class dummy: pass
            style = dummy()
            # The nocolor palette has all available roles.
            # Use that pallete as the basis for populating
            # the palette as defined in the environment.
            for role in termcolors.PALETTES[termcolors.NOCOLOR_PALETTE]:
                format = color_settings.get(role,{})
                setattr(style, role, termcolors.make_style(**format))
            # For backwards compatibility,
            # set style for ERROR_OUTPUT == ERROR
            style.ERROR_OUTPUT = style.ERROR
        else:
            style = no_style()
    return style

def no_style():
    """Returns a Style object that has no colors."""
    class dummy:
        def __getattr__(self, attr):
            return lambda x: x
    return dummy()

########NEW FILE########
__FILENAME__ = select_result
#!/usr/bin/python
#-*-coding:utf-8-*-

import types
from w3lib.html import remove_entities
from urlparse import urlparse, urljoin

NULL = [None,'null']

list_first_item = lambda x:x[0] if x else None

def strip_null(arg,null=None):
    """
        strip list,set,tuple,dict null item.

        @param:
            arg:the variable to strip null
            null:the null definition,if it is None,then use NULL as the null

        if arg is list,then strip the null item,return the new list
        if arg is tuple,then strip the null item,return the new tuple
        if arg is set,then strip the null item,return the new set
        if arg is dict,then strip the dict item which value is null.return the new dict
    """
    if null is None:
        null = NULL

    if type(arg) is types.ListType:
        return [i for i in arg if i not in null]
    elif type(arg) is types.TupleType:
        return tuple([i for i in arg if i not in null])
    elif type(arg) is type(set()):
        return arg.difference(set(null))
    elif type(arg) is types.DictType:
        return {key:value for key,value in arg.items() if value not in null}

    return arg

def deduplication(arg):
    """
        deduplication the arg.

        @param:
            arg:the variable to deduplication

        if arg is list,then deduplication it and then the new list.
        if arg is tuple,then deduplication it and then the new tuple.
    """
    if type(arg) is types.ListType:
        return list(set(arg))
    elif type(arg) is types.TupleType:
        return tuple(set(arg))

    return arg

def clean_link(link_text):
    """
        Remove leading and trailing whitespace and punctuation
    """

    return link_text.strip("\t\r\n '\"")

clean_url = lambda base_url,u,response_encoding: urljoin(base_url, remove_entities(clean_link(u.decode(response_encoding))))
"""
    remove leading and trailing whitespace and punctuation and entities from the given text.
    then join the base_url and the link that extract
"""

########NEW FILE########
__FILENAME__ = termcolors
#!/usr/bin/python
#-*- coding:utf-8 -*-
"""
termcolors.py
"""

color_names = ('black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')
foreground = dict([(color_names[x], '3%s' % x) for x in range(8)])
background = dict([(color_names[x], '4%s' % x) for x in range(8)])

RESET = '0'
opt_dict = {'bold': '1', 'underscore': '4', 'blink': '5', 'reverse': '7', 'conceal': '8'}


def colorize(text='', opts=(), **kwargs):
    """
    Returns your text, enclosed in ANSI graphics codes.

    Depends on the keyword arguments 'fg' and 'bg', and the contents of
    the opts tuple/list.

    Returns the RESET code if no parameters are given.

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold'
        'underscore'
        'blink'
        'reverse'
        'conceal'
        'noreset' - string will not be auto-terminated with the RESET code

    Examples:
        colorize('hello', fg='red', bg='blue', opts=('blink',))
        colorize()
        colorize('goodbye', opts=('underscore',))
        print colorize('first line', fg='red', opts=('noreset',))
        print 'this should be red too'
        print colorize('and so should this')
        print 'this should not be red'
    """
    code_list = []
    if text == '' and len(opts) == 1 and opts[0] == 'reset':
        return '\x1b[%sm' % RESET
    for k, v in kwargs.iteritems():
        if k == 'fg':
            code_list.append(foreground[v])
        elif k == 'bg':
            code_list.append(background[v])
    for o in opts:
        if o in opt_dict:
            code_list.append(opt_dict[o])
    if 'noreset' not in opts:
        text = text + '\x1b[%sm' % RESET
    return ('\x1b[%sm' % ';'.join(code_list)) + text

def make_style(opts=(), **kwargs):
    """
    Returns a function with default parameters for colorize()

    Example:
        bold_red = make_style(opts=('bold',), fg='red')
        print bold_red('hello')
        KEYWORD = make_style(fg='yellow')
        COMMENT = make_style(fg='blue', opts=('bold',))
    """
    return lambda text: colorize(text, opts, **kwargs)

NOCOLOR_PALETTE = 'nocolor'
DARK_PALETTE = 'dark'
LIGHT_PALETTE = 'light'

PALETTES = {
    NOCOLOR_PALETTE: {
        'ERROR':        {},
        'NOTICE':       {},
        'SQL_FIELD':    {},
        'SQL_COLTYPE':  {},
        'SQL_KEYWORD':  {},
        'SQL_TABLE':    {},
        'HTTP_INFO':         {},
        'HTTP_SUCCESS':      {},
        'HTTP_REDIRECT':     {},
        'HTTP_NOT_MODIFIED': {},
        'HTTP_BAD_REQUEST':  {},
        'HTTP_NOT_FOUND':    {},
        'HTTP_SERVER_ERROR': {},
    },
    DARK_PALETTE: {
        'ERROR':        { 'fg': 'red', 'opts': ('bold',) },
        'NOTICE':       { 'fg': 'yellow' },
        'SQL_FIELD':    { 'fg': 'green', 'opts': ('bold',) },
        'SQL_COLTYPE':  { 'fg': 'green' },
        'SQL_KEYWORD':  { 'fg': 'yellow' },
        'SQL_TABLE':    { 'opts': ('bold',) },
        'HTTP_INFO':         { 'opts': ('bold',) },
        'HTTP_SUCCESS':      { },
        'HTTP_REDIRECT':     { 'fg': 'green' },
        'HTTP_NOT_MODIFIED': { 'fg': 'cyan' },
        'HTTP_BAD_REQUEST':  { 'fg': 'red', 'opts': ('bold',) },
        'HTTP_NOT_FOUND':    { 'fg': 'yellow' },
        'HTTP_SERVER_ERROR': { 'fg': 'magenta', 'opts': ('bold',) },
    },
    LIGHT_PALETTE: {
        'ERROR':        { 'fg': 'red', 'opts': ('bold',) },
        'NOTICE':       { 'fg': 'yellow' },
        'SQL_FIELD':    { 'fg': 'green', 'opts': ('bold',) },
        'SQL_COLTYPE':  { 'fg': 'green' },
        'SQL_KEYWORD':  { 'fg': 'blue' },
        'SQL_TABLE':    { 'opts': ('bold',) },
        'HTTP_INFO':         { 'opts': ('bold',) },
        'HTTP_SUCCESS':      { },
        'HTTP_REDIRECT':     { 'fg': 'green', 'opts': ('bold',) },
        'HTTP_NOT_MODIFIED': { 'fg': 'green' },
        'HTTP_BAD_REQUEST':  { 'fg': 'red', 'opts': ('bold',) },
        'HTTP_NOT_FOUND':    { 'fg': 'red' },
        'HTTP_SERVER_ERROR': { 'fg': 'magenta', 'opts': ('bold',) },
    }
}
DEFAULT_PALETTE = DARK_PALETTE

def parse_color_setting(config_string):
    """Parse a SPIDER_COLORS environment variable to produce the system palette

    The general form of a pallete definition is:

        "palette;role=fg;role=fg/bg;role=fg,option,option;role=fg/bg,option,option"

    where:
        palette is a named palette; one of 'light', 'dark', or 'nocolor'.
        role is a named style used by SPIDER
        fg is a background color.
        bg is a background color.
        option is a display options.

    Specifying a named palette is the same as manually specifying the individual
    definitions for each role. Any individual definitions following the pallete
    definition will augment the base palette definition.

    Valid roles:
        'error', 'notice', 'sql_field', 'sql_coltype', 'sql_keyword', 'sql_table',
        'http_info', 'http_success', 'http_redirect', 'http_bad_request',
        'http_not_found', 'http_server_error'

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold', 'underscore', 'blink', 'reverse', 'conceal'

    """
    if not config_string:
        return PALETTES[DEFAULT_PALETTE]

    # Split the color configuration into parts
    parts = config_string.lower().split(';')
    palette = PALETTES[NOCOLOR_PALETTE].copy()
    for part in parts:
        if part in PALETTES:
            # A default palette has been specified
            palette.update(PALETTES[part])
        elif '=' in part:
            # Process a palette defining string
            definition = {}

            # Break the definition into the role,
            # plus the list of specific instructions.
            # The role must be in upper case
            role, instructions = part.split('=')
            role = role.upper()

            styles = instructions.split(',')
            styles.reverse()

            # The first instruction can contain a slash
            # to break apart fg/bg.
            colors = styles.pop().split('/')
            colors.reverse()
            fg = colors.pop()
            if fg in color_names:
                definition['fg'] = fg
            if colors and colors[-1] in color_names:
                definition['bg'] = colors[-1]

            # All remaining instructions are options
            opts = tuple(s for s in styles if s in opt_dict.keys())
            if opts:
                definition['opts'] = opts

            # The nocolor palette has all available roles.
            # Use that palette as the basis for determining
            # if the role is valid.
            if role in PALETTES[NOCOLOR_PALETTE] and definition:
                palette[role] = definition

    # If there are no colors specified, return the empty palette.
    if palette == PALETTES[NOCOLOR_PALETTE]:
        return None
    return palette

########NEW FILE########
