__FILENAME__ = core
# -*- coding: utf-8 -*-


import os
import json
import time
from datetime import datetime
from uuid import uuid4

import redis
import requests
import boto
from boto.s3.connection import S3Connection
from celery import Celery
from flask import Flask, request, Response, jsonify, redirect, url_for
from werkzeug.contrib.cache import RedisCache
from pyelasticsearch import ElasticSearch
from flask.ext.cache import Cache

app = Flask(__name__)
app.debug = os.environ.get('DEBUG')

# Statics.
ELASTICSEARCH_URL = os.environ['ELASTICSEARCH_URL']
S3_BUCKET = os.environ['S3_BUCKET']
S3_BUCKET_DOMAIN = os.environ.get('S3_BUCKET_DOMAIN')
CLOUDAMQP_URL = os.environ.get('CLOUDAMQP_URL')
REDIS_URL = os.environ.get('OPENREDIS_URL')
IA_ACCESS_KEY_ID = os.environ.get('IA_ACCESS_KEY_ID')
IA_SECRET_ACCESS_KEY = os.environ.get('IA_SECRET_ACCESS_KEY')
IA_BUCKET = os.environ.get('IA_BUCKET')
SEARCH_TIMEOUT = 50

# Connection pools.
celery = Celery(broker=CLOUDAMQP_URL)
es = ElasticSearch(ELASTICSEARCH_URL)
bucket = S3Connection().get_bucket(S3_BUCKET)
ia = boto.connect_ia(IA_ACCESS_KEY_ID, IA_SECRET_ACCESS_KEY)
archive = ia.lookup(IA_BUCKET)

cache = Cache()
cache.cache = RedisCache()
cache.cache._client = redis.from_url(REDIS_URL)

class Record(object):
    def __init__(self):
        self.uuid = str(uuid4())
        self.content_type = 'application/octet-stream'
        self.epoch = epoch()
        self.added = epoch()
        self.filename = None
        self.ref = None
        self.description = None
        self.author = None
        self.links = {}
        self.metadata = {}

    @classmethod
    def from_uuid(cls, uuid):
        key = bucket.get_key('{0}.json'.format(uuid))
        j = json.loads(key.read())['record']

        r = cls()
        r.uuid = j.get('uuid')
        r.content_type = j.get('content_type')
        r.epoch = j.get('epoch')
        r.added = j.get('added')
        r.filename = j.get('filename')
        r.ref = j.get('ref')
        r.links = j.get('links')
        r.metadata = j.get('metadata')
        r.description = j.get('description')
        r.author = j.get('author')

        return r

    @classmethod
    def from_hit(cls, hit):
        j = hit['_source']

        r = cls()
        r.uuid = j.get('uuid')
        r.content_type = j.get('content_type')
        r.epoch = j.get('epoch')
        r.added = j.get('added')
        r.filename = j.get('filename')
        r.ref = j.get('ref')
        r.links = j.get('links')
        r.metadata = j.get('metadata')
        r.description = j.get('description')
        r.author = j.get('author')

        return r

    def upload(self, data=None, url=None, archive=False):

        if url:
            r = requests.get(url)
            data = r.content

        if data:
            key = bucket.new_key(self.uuid)

            if self.content_type:
                key.update_metadata({'Content-Type': self.content_type})

            key.set_contents_from_string(data)
            key.make_public()

        if archive:
            self.archive_upload(data=data, url=url)

    @celery.task
    def upload_task(self, **kwargs):
        self.upload(**kwargs)

    @celery.task
    def index_task(self, **kwargs):
        self.index(**kwargs)

    @celery.task(rate_limit='30/m')
    def archive_task(self, **kwargs):
        self.archive(**kwargs)

    @property
    def content(self):
        key = bucket.get_key(self.uuid)
        return key.read()

    @property
    def content_url(self):
        prefix = 'http://{}.s3.amazonaws.com'.format(S3_BUCKET)

        if S3_BUCKET_DOMAIN:
            prefix = 'http://{}'.format(S3_BUCKET_DOMAIN)

        return '{}/{}'.format(prefix, self.uuid)

    @property
    def meta_url(self):
        return '{}.json'.format(self.content_url)

    @property
    def content_archive(self):
        return 'http://archive.org/download/{}/{}'.format(IA_BUCKET, self.uuid)

    @property
    def meta_archive(self):
        return '{}.json'.format(self.content_archive)

    def save(self, archive=False):

        self.persist()
        self.index()

        if archive:
            self.archive(upload=False)

    def persist(self):
        key = bucket.new_key('{0}.json'.format(self.uuid))
        key.update_metadata({'Content-Type': 'application/json'})

        key.set_contents_from_string(self.json)
        key.make_public()


    def index(self):
         es.index("archives", "record", self.dict, id=self.uuid)

    def archive(self, upload=False):

        key_name = '{0}.json'.format(self.uuid)

        key = archive.new_key(key_name)
        key.update_metadata({'Content-Type': 'application/json'})

        key.set_contents_from_string(self.json)

        if upload:
            self.archive_upload(url=self.content_url)

    def archive_upload(self, data=None, url=None):
        if url:
            r = requests.get(url)
            data = r.content

        if data:
            key = archive.new_key(self.uuid)

            if self.content_type:
                key.update_metadata({'Content-Type': self.content_type})

            key.set_contents_from_string(data)

    @property
    def dict(self):
        return {
            'uuid': self.uuid,
            'content_type': self.content_type,
            'epoch': self.epoch,
            'added': self.added,
            'filename': self.filename,
            'ref': self.ref,
            'links': self.links,
            'metadata': self.metadata,
            'description': self.description,
            'author': self.author
        }

    @property
    def json(self):
        return json.dumps({'record': self.dict})

    def __repr__(self):
        return '<Record {0}>'.format(self.uuid)


def epoch(dt=None):
    if not dt:
        dt = datetime.utcnow()

    return int(time.mktime(dt.timetuple()) * 1000 + dt.microsecond / 1000)

def iter_search(query, **kwargs):

    if query is None:
        query = '*'
    # Pepare elastic search queries.
    params = {}
    for (k, v) in kwargs.items():
        params['es_{0}'.format(k)] = v

    params['es_q'] = query

    q = {
        'sort': [
            {"epoch" : {"order" : "desc"}},
        ]
    }

    # if query:
    q['query'] = {'term': {'query': query}},


    results = es.search(q, index='archives', **params)
    # print results

    params['es_q'] = query
    for hit in results['hits']['hits']:
        yield Record.from_hit(hit)

@cache.memoize(timeout=SEARCH_TIMEOUT)
def search(query, sort=None, size=None, **kwargs):
    if sort is not None:
        kwargs['sort'] = sort
    if size is not None:
        kwargs['size'] = size

    return [r for r in iter_search(query, **kwargs)]

@app.route('/')
def hello():
    j = {
        'source': 'https://github.com/kennethreitz/blackbox',
        'curator': 'Kenneth Reitz',
        'resources': {
            '/records': 'The collection of records.',
            '/records/:id': 'The metadata of the given record.',
            '/records/:id/download': 'The content of the given record.',
        }
    }
    return jsonify(blackbox=j)

@app.route('/records/')
def get_records():

    args = request.args.to_dict()
    results = search(request.args.get('q'), **args)

    def gen():
        for result in results:
            d = result.dict
            d['links']['path:meta'] = result.meta_url
            d['links']['path:data'] = result.content_url
            d['links']['archive:meta'] = result.meta_archive
            d['links']['archive:data'] = result.content_archive

            yield d

    return jsonify(records=[r for r in gen()])

@app.route('/records/<uuid>')
def get_record(uuid):
    r = Record.from_uuid(uuid)
    return jsonify(record=r.dict)

@app.route('/records/<uuid>/download')
def download_record(uuid):
    r = Record.from_uuid(uuid)
    return redirect(r.content_url)



if __name__ == '__main__':
    app.run()
########NEW FILE########
__FILENAME__ = tasks
from .core import *
########NEW FILE########
__FILENAME__ = archive
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Archive importer.

Usage:
  archive.py <url> [--description=<t>] [--author=<a>]

Options:
  --description=<t>   Description of archive.
  --author=<a>        Author of archive.
"""

from _util import *
from docopt import docopt

def main(url, description=None, author='Kenneth Reitz'):

    if description is None:
        description = 'Archive of {}'.format(url)

        r = blackbox.Record()
        r.ref = url
        r.description = description
        r.author = author
        r.filename = url.split('/')[-1] or None

        r.metadata['archive'] = True

        r.save()
        r.upload_task.delay(r, url=url)

if __name__ == '__main__':
    arguments = docopt(__doc__, version='Archive Importer')
    args = {
        'url': arguments['<url>'],
        'description': arguments['--description'],
        'author': arguments['--author']
    }
    main(**args)
########NEW FILE########
__FILENAME__ = dupes
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Dupes Remover.

Usage:
  dupes.py [--dry]

Options:
  -h --help     Show this screen.
  -d --dry      Executes a dry run.
"""

import json
from _util import *
from docopt import docopt
from clint.textui import progress

# {service: {service-key: [keys]}}

db = {
    'instagram': {},
    'twitter': {}
}
dupes = set()
contentless = set()

service_keys = {
    'instagram': 'id',
    'twitter': 'id'
}

def sort_dupes(j):

    service = j['metadata'].get('service')

    if service in service_keys:
        ident_k = service_keys[service]
        ident = j['metadata'][ident_k]
        uuid = j['uuid']

        if db[service].get(ident) is None:
            db[service][ident] = []
        else:
            dupes.add(uuid)

        db[service][ident].append(uuid)


def has_content(uuid):
    # logger.info('Checking content of {}'.format(uuid))
    return uuid in blackbox.bucket

def remove(uuid, dry=False):
    print 'removing', uuid
    if not dry:
        try:
            blackbox.es.delete('archives', 'record', uuid)
        except Exception:
            pass
        try:
            blackbox.bucket.delete_key('{}.json'.format(uuid))
        except Exception:
            pass
        try:
            blackbox.bucket.delete_key(uuid)
        except Exception:
            pass


def iter_metadata():
    for key in blackbox.bucket:
        if key.name.endswith('.json'):
            yield key

def main(dry=False):
    print 'Iterating over keys...'

    for key in progress.bar(list(iter_metadata())):
        j = json.loads(key.get_contents_as_string())['record']

        uuid = j['uuid']

        if not has_content(uuid):
            contentless.add(uuid)
        else:
            sort_dupes(j)

    print 'Deleting {} contentless found...'.format(len(contentless))
    for k in list(contentless):
        remove(k, dry=dry)

    print 'Deleting {} dupes found...'.format(len(dupes))
    for dupe in dupes:
        remove(dupe, dry=dry)




if __name__ == '__main__':
    arguments = docopt(__doc__, version='Dupes Remover')
    main(dry=arguments['--dry'])
########NEW FILE########
__FILENAME__ = flickr
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Flickr importer.

Usage:
  flickr.py [--update] [--dry]

Options:
  -h --help     Show this screen.
  -u --update   Update existing records.
  -d --dry      Executes a dry run.
"""



from _util import *
from docopt import docopt

URL = 'https://secure.flickr.com/services/rest/?method=flickr.people.getPhotos&user_id=me&per_page=100&format=json&nojsoncallback=1&extras=description,date_upload,date_taken,original_format,geo,path_alias,url_o'

def lookup_record(photo):

    try:
        return blackbox.iter_search('metadata.service:flickr AND metadata.id:{}'.format(photo['id'])).next()
    except Exception:
        return None


def iter_photos():

    r = foauth.get(URL)
    j = r.json()

    for page in range(j['photos']['pages']+1):
        r = foauth.get(URL, params={'page': page})
        j = r.json()
        for photo in j['photos']['photo']:
            yield photo



def main(update=False, dry=False):

    for photo in iter_photos():

        existing = lookup_record(photo)
        if existing:
            print 'Existing:',

            if not update:
                print '{0}. \nExiting.'.format(existing)
                return


        r = existing or blackbox.Record()

        r.content_type = 'image/jpeg'
        r.ref = 'http://www.flickr.com/photos/{}/{}'.format(photo['pathalias'], photo['id'])
        r.description = u'Flickr photo. {}'.format(photo['title'])
        r.author = 'Kenneth Reitz'
        r.links['src'] = photo['url_o']
        r.epoch = int(photo[u'dateupload'])*1000

        r.metadata['id'] = photo['id']
        r.metadata['service'] = 'flickr'
        r.metadata['title'] = photo['title']
        r.metadata['taken'] = epoch(parse(photo[u'datetaken']))
        r.metadata['longitude'] = photo['longitude']
        r.metadata['latitude'] = photo['latitude']

        print r

        if not dry:
            r.save(archive=True)

            r.upload_task.delay(r, url=photo['url_o'], archive=True)



if __name__ == '__main__':
    arguments = docopt(__doc__, version='Flickr Importer')
    main(update=arguments['--update'], dry=arguments['--dry'])
########NEW FILE########
__FILENAME__ = gist

########NEW FILE########
__FILENAME__ = github

########NEW FILE########
__FILENAME__ = instagram
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Instagram importer.

Usage:
  instagram.py [--update] [--dry]

Options:
  -h --help     Show this screen.
  -u --update   Update existing records.
  -d --dry      Executes a dry run.
"""



from _util import *
from docopt import docopt


URL = 'https://api.instagram.com/v1/users/self/media/recent'

def lookup_record(photo):

    try:
        return blackbox.iter_search('metadata.service:instagram AND metadata.id:{}'.format(photo['id'])).next()
    except Exception:
        return None

def iter_pages():
    r = foauth.get(URL)

    yield r.json()

    next = r.json()['pagination'].get('next_max_id')

    while next:
        r = foauth.get(URL, params={'max_id': next})

        yield r.json()

        next = r.json()['pagination'].get('next_max_id')


def iter_photos():

    for page in iter_pages():
        for i in page['data']:

            j = {
                'id': i['id'],
                'url': i['images']['standard_resolution']['url'],
                'link': i['link'],
                'location': i.get('location'),
                'filter': i['filter'],
                'caption': i['caption']['text'] if i.get('caption') else None,
                'created': int(i['created_time'])
            }

            yield j


def main(update=False, dry=False):
    for photo in iter_photos():

        existing = lookup_record(photo)
        if existing:
            print 'Existing:',

            if not update:
                print '{0}. \nExiting.'.format(existing)
                return

        r = existing or blackbox.Record()

        r.content_type = 'image/jpeg'
        r.ref = photo['link']
        r.description = 'Instagram by @kennethreitz. Caption: {}'.format(photo['caption'])
        r.author = 'Kenneth Reitz'
        r.links['src'] = photo['url']
        r.epoch = photo['created'] * 1000

        r.metadata['id'] = photo['id']
        r.metadata['service'] = 'instagram'
        r.metadata['filter'] = photo['filter']
        r.metadata['location'] = photo['location']
        r.metadata['caption'] = photo['caption']

        if not dry:
            r.save(archive=True)

            r.upload_task.delay(r, url=photo['url'], archive=True)
        print r



if __name__ == '__main__':
    arguments = docopt(__doc__, version='Instagram Importer')
    main(update=arguments['--update'], dry=arguments['--dry'])
########NEW FILE########
__FILENAME__ = photos500px
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""500px importer.

Usage:
  photos-500px.py [--update] [--dry]

Options:
  -h --help     Show this screen.
  -u --update   Update existing records.
  -d --dry      Executes a dry run.
"""


from _util import *
from docopt import docopt


username = foauth.get('https://api.500px.com/v1/users/').json()['user']['username']

def lookup_record(photo):

    try:
        return blackbox.iter_search('metadata.service:500px AND metadata.id:{}'.format(photo['id'])).next()
    except Exception:
        return None

def iter_photos():
    r = foauth.get('https://api.500px.com/v1/photos?feature=user&username={}'.format(username))
    total_pages = r.json()['total_pages']

    for i in range(total_pages):
        r = foauth.get('https://api.500px.com/v1/photos?feature=user&username={}&page={}'.format(username, i+1))
        for photo in r.json()['photos']:
            yield photo

def main(update=False, dry=False):
    for photo in iter_photos():

        existing = lookup_record(photo)
        if existing:
            print 'Existing:',

            if not update:
                print '{0}. \nExiting.'.format(existing)
                return

        r = existing or blackbox.Record()
        r.content_type = 'image/jpeg'
        r.ref = 'http://500px.com/photo/{}'.format(photo['id'])
        r.description = u'500px: {}, '.format(photo['name'], photo['description'])
        r.author = 'Kenneth Reitz'
        r.epoch = epoch(parse(photo[u'created_at']))

        r.metadata['service'] = '500px'
        r.metadata['height'] = photo['height']
        r.metadata['width'] = photo['width']
        r.metadata['id'] = photo['id']
        r.metadata['name'] = photo['name']
        r.metadata['description'] = photo['width']
        r.metadata['nsfw'] = photo['nsfw']
        r.metadata['src'] = photo['image_url'].replace('2.jpg', '4.jpg')

        if not dry:
            r.save(archive=True)

            r.upload_task.delay(r, url=photo['image_url'].replace('2.jpg', '4.jpg'), archive=True)
        print r

if __name__ == '__main__':
    arguments = docopt(__doc__, version='500px Importer')
    main(update=arguments['--update'], dry=arguments['--dry'])


########NEW FILE########
__FILENAME__ = soundcloud
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""SoundCloud importer.

Usage:
  soundcloud.py [--update] [--dry]

Options:
  -h --help     Show this screen.
  -u --update   Update existing records.
  -d --dry      Executes a dry run.
"""

from _util import *
from docopt import docopt

########NEW FILE########
__FILENAME__ = twitter
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Twitter importer.

Usage:
  twitter.py [--update] [--dry] [--pages=<p>]

Options:
  -h --help     Show this screen.
  -u --update   Update existing records.
  -d --dry      Executes a dry run.
  --pages=<p>   Number of pages to pull [default: 1].
"""

import json

from _util import *
from docopt import docopt

TIMELINE_URL = 'https://api.twitter.com/1/statuses/user_timeline.json'

def iter_tweets(exclude_replies=True, pages=1):

    params = {
        'exclude_replies': exclude_replies,
        'include_entities': True,
        'trim_user': True,
        'contributor_details': True,
        # 'max_id': '285391183943962624'
    }

    for page in range(pages):

        r = foauth.get(TIMELINE_URL, params=params)

        for tweet in r.json():
            yield tweet

        params['max_id'] = tweet['id']


def lookup_record(tweet):

    try:
        return blackbox.iter_search('metadata.service:twitter AND metadata.id:{}'.format(tweet['id'])).next()
    except Exception:
        return None


def main(update=False, dry=False, pages=1):
    for tweet in iter_tweets(pages=pages):
        existing = lookup_record(tweet)
        if existing:
            print 'Existing:',

            if not update:
                print '{0}. \nExiting.'.format(existing)
                return

        r = existing or blackbox.Record()
        r.epoch = epoch(parse(tweet[u'created_at']))
        r.content_type = 'application/json'
        r.ref = 'https://twitter.com/kennethreitz/status/{}'.format(tweet['id'])
        r.author = 'Kenneth Reitz'

        r.description = u'Tweet: {}'.format(tweet['text'])
        r.metadata['service'] = 'twitter'
        r.metadata['id'] = tweet['id']
        r.metadata['text'] = tweet['text']
        r.metadata['retweeted'] = tweet['retweeted']
        r.metadata['retweet_count'] = tweet['retweet_count']
        r.metadata['entities'] = tweet['entities']
        r.metadata['coordinates'] = tweet.get('coordinates')

        if not dry:
            r.save(archive=True)

            r.upload_task.delay(r, data=json.dumps(tweet), archive=True)
        print r







if __name__ == '__main__':
    arguments = docopt(__doc__, version='Twitter Importer')
    main(update=arguments['--update'], dry=arguments['--dry'], pages=int(arguments['--pages']))

########NEW FILE########
__FILENAME__ = vimeo

########NEW FILE########
__FILENAME__ = _util
# -*- coding: utf-8 -*-

"""This module contains shares utilities that are used for all importers."""

import os
import sys

from requests import Session
from requests_foauth import Foauth

sys.path.insert(0, os.path.abspath('..'))
import blackbox
from dateutil.parser import parse
from blackbox import epoch

foauth = Session()
foauth.mount('http', Foauth(os.environ['FOAUTH_USER'], os.environ['FOAUTH_PASS']))

# box = Session()
# box.auth = (os.environ['SECRET_KEY'], os.environ['SECRET_KEY'])

import logging
logger = logging.getLogger()
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

from flask.ext.script import Manager
from clint.textui import progress
import importers
from blackbox import *

def iter_metadata():
    for key in bucket.list():
        if key.name.endswith('.json'):
            yield key

manager = Manager(app)

# TODO: purge elasticsearch
# TODO: seed elasticsearch

@manager.command
def hello():
    print "hello"


@manager.command
def purge_index():
    es.delete_index('archives')

@manager.command
def seed_index():
    print 'Indexing:'
    for key in progress.bar([i for i in iter_metadata()]):
        r = Record.from_uuid(key.name[:-5])
        r.index_task.delay(r)

@manager.command
def seed_archive():
    print 'Archiving:'
    archive_keys = [key.name for key in archive.list()]

    for key in progress.bar([i for i in iter_metadata()]):
        if key.name not in archive_keys:
            r = Record.from_uuid(key.name[:-5])
            r.archive_task.delay(r)

@manager.command
def dupes():
    importers.dupes.main(dry=False)

@manager.command
def imports():
    print 'Importing Instagram'
    importers.instagram.main(dry=False)

    print 'Importing 500px'
    importers.photos500px.main(dry=False)

    print 'Importing Twitter'
    importers.twitter.main(dry=False, pages=2, update=False)

    print 'Importing Flickr'
    importers.flickr.main(dry=False)


if __name__ == "__main__":
    manager.run()
########NEW FILE########
