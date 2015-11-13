__FILENAME__ = dj_database_url
# -*- coding: utf-8 -*-

import os

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse



# Register database schemes in URLs.
urlparse.uses_netloc.append('postgres')
urlparse.uses_netloc.append('postgresql')
urlparse.uses_netloc.append('pgsql')
urlparse.uses_netloc.append('postgis')
urlparse.uses_netloc.append('mysql')
urlparse.uses_netloc.append('mysql2')
urlparse.uses_netloc.append('mysqlgis')
urlparse.uses_netloc.append('spatialite')
urlparse.uses_netloc.append('sqlite')

DEFAULT_ENV = 'DATABASE_URL'

SCHEMES = {
    'postgres': 'django.db.backends.postgresql_psycopg2',
    'postgresql': 'django.db.backends.postgresql_psycopg2',
    'pgsql': 'django.db.backends.postgresql_psycopg2',
    'postgis': 'django.contrib.gis.db.backends.postgis',
    'mysql': 'django.db.backends.mysql',
    'mysql2': 'django.db.backends.mysql',
    'mysqlgis': 'django.contrib.gis.db.backends.mysql',
    'spatialite': 'django.contrib.gis.db.backends.spatialite',
    'sqlite': 'django.db.backends.sqlite3',
}


def config(env=DEFAULT_ENV, default=None, engine=None):
    """Returns configured DATABASE dictionary from DATABASE_URL."""

    config = {}

    s = os.environ.get(env, default)

    if s:
        config = parse(s, engine)

    return config


def parse(url, engine=None):
    """Parses a database URL."""

    if url == 'sqlite://:memory:':
        # this is a special case, because if we pass this URL into
        # urlparse, urlparse will choke trying to interpret "memory"
        # as a port number
        return {
            'ENGINE': SCHEMES['sqlite'],
            'NAME': ':memory:'
        }
        # note: no other settings are required for sqlite

    # otherwise parse the url as normal
    config = {}

    url = urlparse.urlparse(url)

    # Remove query strings.
    path = url.path[1:]
    path = path.split('?', 2)[0]

    # if we are using sqlite and we have no path, then assume we
    # want an in-memory database (this is the behaviour of sqlalchemy)
    if url.scheme == 'sqlite' and path == '':
        path = ':memory:'

    # Update with environment configuration.
    config.update({
        'NAME': path or '',
        'USER': url.username or '',
        'PASSWORD': url.password or '',
        'HOST': url.hostname or '',
        'PORT': url.port or '',
    })

    if engine:
        config['ENGINE'] = engine
    elif url.scheme in SCHEMES:
        config['ENGINE'] = SCHEMES[url.scheme]

    return config

########NEW FILE########
__FILENAME__ = test_dj_database_url
# -*- coding: utf-8 -*-
#!/usr/bin/env python

import os
import unittest

import dj_database_url


POSTGIS_URL = 'postgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn'


class DatabaseTestSuite(unittest.TestCase):

    def test_postgres_parsing(self):
        url = 'postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn'
        url = dj_database_url.parse(url)

        assert url['ENGINE'] == 'django.db.backends.postgresql_psycopg2'
        assert url['NAME'] == 'd8r82722r2kuvn'
        assert url['HOST'] == 'ec2-107-21-253-135.compute-1.amazonaws.com'
        assert url['USER'] == 'uf07k1i6d8ia0v'
        assert url['PASSWORD'] == 'wegauwhgeuioweg'
        assert url['PORT'] == 5431

    def test_postgis_parsing(self):
        url = 'postgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn'
        url = dj_database_url.parse(url)

        assert url['ENGINE'] == 'django.contrib.gis.db.backends.postgis'
        assert url['NAME'] == 'd8r82722r2kuvn'
        assert url['HOST'] == 'ec2-107-21-253-135.compute-1.amazonaws.com'
        assert url['USER'] == 'uf07k1i6d8ia0v'
        assert url['PASSWORD'] == 'wegauwhgeuioweg'
        assert url['PORT'] == 5431

    def test_mysql_gis_parsing(self):
        url = 'mysqlgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn'
        url = dj_database_url.parse(url)

        assert url['ENGINE'] == 'django.contrib.gis.db.backends.mysql'
        assert url['NAME'] == 'd8r82722r2kuvn'
        assert url['HOST'] == 'ec2-107-21-253-135.compute-1.amazonaws.com'
        assert url['USER'] == 'uf07k1i6d8ia0v'
        assert url['PASSWORD'] == 'wegauwhgeuioweg'
        assert url['PORT'] == 5431

    def test_cleardb_parsing(self):
        url = 'mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com/heroku_97681db3eff7580?reconnect=true'
        url = dj_database_url.parse(url)

        assert url['ENGINE'] == 'django.db.backends.mysql'
        assert url['NAME'] == 'heroku_97681db3eff7580'
        assert url['HOST'] == 'us-cdbr-east.cleardb.com'
        assert url['USER'] == 'bea6eb025ca0d8'
        assert url['PASSWORD'] == '69772142'
        assert url['PORT'] is ''

    def test_database_url(self):
        del os.environ['DATABASE_URL']
        a = dj_database_url.config()
        assert not a

        os.environ['DATABASE_URL'] = 'postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn'

        url = dj_database_url.config()

        assert url['ENGINE'] == 'django.db.backends.postgresql_psycopg2'
        assert url['NAME'] == 'd8r82722r2kuvn'
        assert url['HOST'] == 'ec2-107-21-253-135.compute-1.amazonaws.com'
        assert url['USER'] == 'uf07k1i6d8ia0v'
        assert url['PASSWORD'] == 'wegauwhgeuioweg'
        assert url['PORT'] == 5431

    def test_empty_sqlite_url(self):
        url = 'sqlite://'
        url = dj_database_url.parse(url)

        assert url['ENGINE'] == 'django.db.backends.sqlite3'
        assert url['NAME'] == ':memory:'

    def test_memory_sqlite_url(self):
        url = 'sqlite://:memory:'
        url = dj_database_url.parse(url)

        assert url['ENGINE'] == 'django.db.backends.sqlite3'
        assert url['NAME'] == ':memory:'

    def test_parse_engine_setting(self):
        engine = 'django_mysqlpool.backends.mysqlpool'
        url = 'mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com/heroku_97681db3eff7580?reconnect=true'
        url = dj_database_url.parse(url, engine)

        assert url['ENGINE'] == engine

    def test_config_engine_setting(self):
        engine = 'django_mysqlpool.backends.mysqlpool'
        os.environ['DATABASE_URL'] = 'mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com/heroku_97681db3eff7580?reconnect=true'
        url = dj_database_url.config(engine=engine)

        assert url['ENGINE'] == engine

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
