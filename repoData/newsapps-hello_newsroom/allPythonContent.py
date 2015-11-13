__FILENAME__ = fabfile
# Chicago Tribune News Applications fabfile
# No copying allowed

from fabric.api import *

"""
Base configuration
"""
env.project_name = 'hello_newsroom'
env.database_password = '5IQZe7WEix'
env.site_media_prefix = "site_media"
env.admin_media_prefix = "admin_media"
env.path = '/home/newsapps/sites/%(project_name)s' % env
env.log_path = '/home/newsapps/logs/%(project_name)s' % env
env.env_path = '%(path)s/env' % env
env.repo_path = '%(path)s/repository' % env
env.apache_config_path = '/home/newsapps/sites/apache/%(project_name)s' % env
env.python = 'python2.6'
env.repository_url = 'your_git_repository_url'
env.multi_server = False
env.memcached_server_address = "cache.example.com"

"""
Environments
"""
def production():
    """
    Work on production environment
    """
    env.settings = 'production'
    env.user = 'newsapps'
    env.hosts = ['db.example.com']
    # Install your SSH public key in the 'authorized_keys' file for the above user on the above host,
    # or specify the path to your private key in env.key_filename below.
    # see http://www.eng.cam.ac.uk/help/jpmg/ssh/authorized_keys_howto.html for more info.
    # env.key_filename = 'path_to_your_key_file.pem'
    env.s3_bucket = 'media.apps.chicagotribune.com'

def staging():
    """
    Work on staging environment
    """
    env.settings = 'staging'
    env.user = 'newsapps'
    env.hosts = ['your-ec2-instance-dns-name.amazonaws.com'] 
    # Install your SSH public key in the 'authorized_keys' file for the above user on the above host,
    # or specify the path to your private key in env.key_filename below.
    # see http://www.eng.cam.ac.uk/help/jpmg/ssh/authorized_keys_howto.html for more info.
    # env.key_filename = 'path_to_your_key_file.pem'
    env.s3_bucket = 'your-bucket-name.s3.amazonaws.com'
    
"""
Branches
"""
def stable():
    """
    Work on stable branch.
    """
    env.branch = 'stable'

def master():
    """
    Work on development branch.
    """
    env.branch = 'master'

def branch(branch_name):
    """
    Work on any specified branch.
    """
    env.branch = branch_name
    
"""
Commands - setup
"""
def setup():
    """
    Setup a fresh virtualenv, install everything we need, and fire up the database.
    
    Does NOT perform the functions of deploy().
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])
    
    setup_directories()
    setup_virtualenv()
    clone_repo()
    checkout_latest()
    destroy_database()
    create_database()
    load_data()
    install_requirements()
    install_apache_conf()

def setup_directories():
    """
    Create directories necessary for deployment.
    """
    run('mkdir -p %(path)s' % env)
    run('mkdir -p %(env_path)s' % env)
    run ('mkdir -p %(log_path)s;' % env)
    sudo('chgrp -R www-data %(log_path)s; chmod -R g+w %(log_path)s;' % env)
    run('ln -s %(log_path)s %(path)s/logs' % env)
    
def setup_virtualenv():
    """
    Setup a fresh virtualenv.
    """
    run('virtualenv -p %(python)s --no-site-packages %(env_path)s;' % env)
    run('source %(env_path)s/bin/activate; easy_install -U setuptools; easy_install pip;' % env)

def clone_repo():
    """
    Do initial clone of the git repository.
    """
    run('git clone %(repository_url)s %(repo_path)s' % env)

def checkout_latest():
    """
    Pull the latest code on the specified branch.
    """
    run('cd %(repo_path)s; git checkout %(branch)s; git pull origin %(branch)s' % env)

def install_requirements():
    """
    Install the required packages using pip.
    """
    run('source %(env_path)s/bin/activate; pip install -E %(env_path)s -r %(repo_path)s/requirements.txt' % env)

def install_apache_conf():
    """
    Install the apache site config file.
    """
    sudo('cp %(repo_path)s/%(project_name)s/configs/%(settings)s/apache %(apache_config_path)s' % env)

"""
Commands - deployment
"""
def deploy():
    """
    Deploy the latest version of the site to the server and restart Apache2.
    
    Does not perform the functions of load_new_data().
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])
    
    with settings(warn_only=True):
        maintenance_up()
        
    checkout_latest()
    gzip_assets()
    deploy_to_s3()
    maintenance_down()
    
def maintenance_up():
    """
    Install the Apache maintenance configuration.
    """
    sudo('cp %(repo_path)s/%(project_name)s/configs/%(settings)s/apache_maintenance %(apache_config_path)s' % env)
    reboot()

def gzip_assets():
    """
    GZips every file in the assets directory and places the new file
    in the gzip directory with the same filename.
    """
    run('cd %(repo_path)s; python gzip_assets.py' % env)

def deploy_to_s3():
    """
    Deploy the latest project site media to S3.
    """
    env.gzip_path = '%(path)s/repository/%(project_name)s/gzip/assets/' % env
    run(('s3cmd -P --add-header=Content-encoding:gzip --guess-mime-type --rexclude-from=%(path)s/repository/s3exclude sync %(gzip_path)s s3://%(s3_bucket)s/%(project_name)s/%(site_media_prefix)s/') % env)
       
def reboot(): 
    """
    Restart the Apache2 server.
    """
    if env.multi_server:
        run('/mnt/apps/bin/restart-all-apache.sh')
    else:
        sudo('service apache2 restart')
    
def maintenance_down():
    """
    Reinstall the normal site configuration.
    """
    install_apache_conf()
    reboot()
    
"""
Commands - rollback
"""
def rollback(commit_id):
    """
    Rolls back to specified git commit hash or tag.
    
    There is NO guarantee we have committed a valid dataset for an arbitrary
    commit hash.
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])
    
    maintenance_up()
    checkout_latest()
    git_reset(commit_id)
    gzip_assets()
    deploy_to_s3()
    maintenance_down()
    
def git_reset(commit_id):
    """
    Reset the git repository to an arbitrary commit hash or tag.
    """
    env.commit_id = commit_id
    run("cd %(repo_path)s; git reset --hard %(commit_id)s" % env)

"""
Commands - data
"""
def load_new_data():
    """
    Erase the current database and load new data from the SQL dump file.
    """
    require('settings', provided_by=[production, staging])
    
    maintenance_up()
    pgpool_down()
    destroy_database()
    create_database()
    load_data()
    pgpool_up()
    maintenance_down()
    
def create_database(func=run):
    """
    Creates the user and database for this project.
    """
    func('echo "CREATE USER %(project_name)s WITH PASSWORD \'%(database_password)s\';" | psql postgres' % env)
    func('createdb -O %(project_name)s %(project_name)s -T template_postgis' % env)
    
def destroy_database(func=run):
    """
    Destroys the user and database for this project.
    
    Will not cause the fab to fail if they do not exist.
    """
    with settings(warn_only=True):
        func('dropdb %(project_name)s' % env)
        func('dropuser %(project_name)s' % env)
        
def load_data():
    """
    Loads data from the repository into PostgreSQL.
    """
    run('psql -q %(project_name)s < %(path)s/repository/data/psql/dump.sql' % env)
    run('psql -q %(project_name)s < %(path)s/repository/data/psql/finish_init.sql' % env)
    
def pgpool_down():
    """
    Stop pgpool so that it won't prevent the database from being rebuilt.
    """
    sudo('/etc/init.d/pgpool stop')
    
def pgpool_up():
    """
    Start pgpool.
    """
    sudo('/etc/init.d/pgpool start')

"""
Commands - miscellaneous
"""
    
def clear_cache():
    """
    Restart memcache, wiping the current cache.
    """
    if env.multi_server:
        run('restart-memcache.sh %(memcached_server_address)' % env)
    else:
        sudo('service memcached restart')
    
def echo_host():
    """
    Echo the current host to the command line.
    """
    run('echo %(settings)s; echo %(hosts)s' % env)

"""
Deaths, destroyers of worlds
"""
def shiva_the_destroyer():
    """
    Remove all directories, databases, etc. associated with the application.
    """
    with settings(warn_only=True):
        run('rm -Rf %(path)s' % env)
        run('rm -Rf %(log_path)s' % env)
        pgpool_down()
        run('dropdb %(project_name)s' % env)
        run('dropuser %(project_name)s' % env)
        pgpool_up()
        sudo('rm %(apache_config_path)s' % env)
        reboot()
        run('s3cmd del --recursive s3://%(s3_bucket)s/%(project_name)s' % env)

"""
Utility functions (not to be called directly)
"""
def _execute_psql(query):
    """
    Executes a PostgreSQL command using the command line interface.
    """
    env.query = query
    run(('cd %(path)s/repository; psql -q %(project_name)s -c "%(query)s"') % env)
    
def bootstrap():
    """
    Local development bootstrap: you should only run this once.
    """    
    create_database(local)
    local("sh ./manage syncdb --noinput")
    local("sh ./manage load_shapefiles")

def shiva_local():
    """
    Undo any local setup.  This will *destroy* your local database, so use with caution.
    """    
    destroy_database(local)
    
########NEW FILE########
__FILENAME__ = gzip_assets
#!/bin/env python

import os
import gzip
import shutil

class FakeTime:
    def time(self):
        return 1261130520.0

# Hack to override gzip's time implementation
# See: http://stackoverflow.com/questions/264224/setting-the-gzip-timestamp-from-python
gzip.time = FakeTime()

project_dir = 'hello_newsroom'

shutil.rmtree(os.path.join(project_dir, 'gzip'), ignore_errors=True)
shutil.copytree(os.path.join(project_dir, 'assets'), os.path.join(project_dir, 'gzip/assets'))

for path, dirs, files in os.walk(os.path.join(project_dir, 'gzip/assets')):
    for filename in files:
        file_path = os.path.join(path, filename)
        
        f_in = open(file_path, 'rb')
        contents = f_in.readlines()
        f_in.close()
        f_out = gzip.open(file_path, 'wb')
        f_out.writelines(contents)
        f_out.close();
########NEW FILE########
__FILENAME__ = dump_sql
"""Dump the SQL data for download
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from optparse import make_option

import os
import re

SUBSTITUTION_PATTERN = re.compile("^(.+?')(.+?)(liblwgeom.+)$")

class Command(BaseCommand):
    option_list= BaseCommand.option_list + (
    make_option('-o', '--sql_output', type='string', action='store', dest='output',
        help='The output file where the SQL data will be dumped.',
        default="data/psql/dump.sql"),
    make_option('-r', '--reverse', type='string', action='store', dest='reverse',
        help='If specified, then the file at [output] will be processed to restore a prefix over $libdir (for Joes broken install) Note that a fresh database dump is NOT made.'),
    )
    def get_version(self):
        return "0.1"

    def handle(self, *args, **options):
        #dump for deployment
        try:
            dumpfile = options['output']
            if options['reverse']:
                prefix = options['reverse']
                substitution(dumpfile,prefix)
                print "Rewrote %s using %s" % (dumpfile,prefix)
            else:    
                os.system('pg_dump -U %s -O -x %s > %s' % (settings.DATABASE_USER,settings.DATABASE_NAME,dumpfile))
                substitution(dumpfile,'$libdir/')
                print('sql dumped to: %s' % dumpfile)
        except KeyError:
            print "You must specify the SQL output file using -o or --sql_output."
            
def substitution(fname,prefix):
    """Find lines referring to the PostGIS extension libraries and adjust the path.  In most PostGIS installs,
       a symbolic path '$libdir' is used to identify the path to 'liblwgeom', but we have some installs that
       use a hard-coded path which doesn't always match when the SQL dump is moved to another server.
    """
    if not prefix.endswith("/"):
        prefix += "/"
    lines = []    
    for line in open(fname).readlines():
        lines.append(fix_line(line,prefix))
    out = open(fname,"w")
    for line in lines:
        out.write(line)
    out.close()    

def fix_line(line,prefix):
    """Return either the given line or a copy of the line with the given prefix in place of the original prefix."""
    parts = SUBSTITUTION_PATTERN.split(line)
    if len(parts) == 1:
        return parts[0]
    else:
        parts = parts[1:-1]    
        parts[1] = prefix
        return "".join(parts)
    

########NEW FILE########
__FILENAME__ = load_shapefiles
"""
    Use code generated by ogrinspect command to initialize GIS data.
    See http://geodjango.org/docs/layermapping.html for more information.
"""
from optparse import make_option

from django.core.management.base import NoArgsCommand, CommandError
from django.contrib.gis.utils import LayerMapping, add_postgis_srs
from django.core import management

from core import models

class Command(NoArgsCommand):
    help=''
    option_list= NoArgsCommand.option_list + ()

    def get_version(self):
        return "0.1"

    def handle_noargs(self, **options):
        
        # These use unusual Spatial Reference System
        # NAD 1983 StatePlane Illinois East FIPS 1201 Feet
        # http://spatialreference.org/ref/esri/102671/
        # This needs to be done before syncdb
#        add_postgis_srs(102671)
        
        management.call_command('syncdb')

        lm = LayerMapping(models.CommunityArea, 'data/maps/community_areas/Community_area.shp', models.communityarea_mapping)
        lm.save(verbose=True)
        print "Community Areas initialized."
        models.CommunityArea.objects.filter(area_number='0').delete()
        print "Bogus Community Areas cleared"
        print
        
        lm = LayerMapping(models.Station, 'data/maps/cta_stations/DATA_ADMIN_CTASTATION.shp', models.station_mapping)
        lm.save(verbose=True)
        print "CTA Stations initialized."
        print

########NEW FILE########
__FILENAME__ = models
from django.contrib.gis.db import models

# This is an auto-generated Django model module created by ogrinspect.
# ./manage ogrinspect data/maps/community_areas/Community_area.shp CommunityArea --name-field=community --srid=4269 --mapping 
# followed by a little trimming/editing

# http://egov.cityofchicago.org/webportal/COCWebPortal/COC_ATTACH/community_area.zip

class CommunityArea(models.Model):
    area_number = models.CharField(max_length=2)
    community = models.CharField(max_length=80)
    geom = models.PolygonField(srid=4269)
    objects = models.GeoManager()

    def __unicode__(self): return self.community

# Auto-generated `LayerMapping` dictionary for CommunityArea model
communityarea_mapping = {
    'area_number' : 'AREA_NUMBE',
    'community' : 'COMMUNITY',
    'geom' : 'POLYGON',
}


class Station(models.Model):
    shortname = models.CharField(max_length=20)
    name = models.CharField(max_length=50)
    lines = models.CharField(max_length=50)
    address = models.CharField(max_length=50)
    ada = models.IntegerField()
    legend = models.CharField(max_length=5)
    alt_legend = models.CharField(max_length=5)
    weblink = models.CharField(max_length=250)
    geom = models.PointField(srid=4269)
    objects = models.GeoManager()

    def __unicode__(self): return self.name


# Auto-generated `LayerMapping` dictionary for Station model
# ./manage ogrinspect data/maps/cta_stations/DATA_ADMIN_CTASTATION.shp Station --name-field=name --srid=4269 --mapping
# followed by a little trimming/editing

# http://egov.cityofchicago.org/webportal/COCWebPortal/COC_EDITORIAL/CTA_Stations.zip
station_mapping = {
    'shortname' : 'SHORTNAME',
    'name' : 'LONGNAME',
    'lines' : 'LINES',
    'address' : 'ADDRESS',
    'ada' : 'ADA',
    'legend' : 'LEGEND',
    'alt_legend' : 'ALT_LEGEND',
    'weblink' : 'WEBLINK',
    'geom' : 'POINT',
}

########NEW FILE########
__FILENAME__ = core
from django import template
from django.conf import settings
from urlparse import urljoin
from urllib import quote_plus

register = template.Library()
 
@register.simple_tag
def url_prefix():
    """Render a suitable prefix for a fully qualified URL.  Designed to work with
    the Django 'url' tag, so this will not include the trailing slash.  Uses
    settings.MY_SITE_DOMAIN and, if defined, settings.MY_SITE_SCHEMA (defaults to http if not defined)
    and settings.MY_SITE_PORT (e.g. 8000; defaults to empty if not defined)"""
    parts = [getattr(settings,'MY_SITE_SCHEMA','http'), '://', getattr(settings,'MY_SITE_DOMAIN')]
    if getattr(settings,'MY_SITE_PORT',False):
        parts.append(':')
        parts.append(settings.MY_SITE_PORT)
    return ''.join(parts)

@register.simple_tag
def build_media_url(uri):
    """
       Take a bit of url (uri) and put it together with the media url
       urljoin doesn't work like you think it would work. It likes to
       throw bits of the url away unless things are just right.
    """
    uri = "/".join(map(quote_plus,uri.split("/")))
    if getattr(settings,'MEDIA_URL',False):
        if uri.startswith('/'):
            return urljoin(settings.MEDIA_URL,uri[1:])
        else:
            return urljoin(settings.MEDIA_URL,uri)
    else:
        return uri

@register.inclusion_tag("core/_gmap.html")
def gmap(gmap_api_version="2"):
    """Return the fragment of JS necessary to inline the Google Maps API on the page, assuming that the Django settings includes
       a value for GOOGLE_MAPS_API_KEY
       """
    assert settings.GOOGLE_MAPS_API_KEY

    return { "gmap_api_version": gmap_api_version,
             "settings": settings 
    }

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin
from core import views

urlpatterns = patterns('',
    url(r'^community_area/(\d+).kml',
        views.comm_area_kml,
    name="comm_area_kml"),
    url(r'',
        views.index,
    name="search"),
)
########NEW FILE########
__FILENAME__ = views
import logging

from django.shortcuts import render_to_response
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.contrib.gis.shortcuts import render_to_kml

from geopy import geocoders

from core import models

log = logging.getLogger("hello_newsroom")

# NOTE: Under load, this strategy is likely to max out your Google API Key. 
# Where possible, geocode addresses using client side calls.
GEOCODER = geocoders.Google()
def index(request):
    template_dict = {}
    try:
        query = request.REQUEST['query']
        client_geocode = request.REQUEST.get('geocode')
        if client_geocode:
            address = request.REQUEST.get('address')
            remainder = None
            point = make_point(client_geocode)
        else:
            log.warn("Geocode was not received in query. Trying to geocode again.")
            address, remainder, point = geocode(query)
            

        template_dict['query'] = query
        template_dict['address'] = address
        template_dict['remainder'] = remainder
        template_dict['point'] = point
        try:
            template_dict['community_area'] = models.CommunityArea.objects.get(geom__contains=point)
        except models.CommunityArea.DoesNotExist:
            pass

        template_dict['stations'] = nearby_stations(point)
    except KeyError:
        pass # no query
    return render_to_response('core/index.html', template_dict)

def comm_area_kml(request, area_number):
    ca = models.CommunityArea.objects.get(area_number=area_number)
    return render_to_kml('core/community_area.kml', {'comm_area': ca })

def geocode(query):
    results = list(GEOCODER.geocode(query,exactly_one=False))
    address = point = remainder = None
    if results:
        first = results[0]
        remainder = results[1:]
        address, lat_lon = first
        point = Point((lat_lon[1], lat_lon[0]))
    
    return (address, remainder, point)

def make_point(lon_lat_str):
    return Point(tuple(map(float,lon_lat_str.split(","))))

def nearby_stations(point):
    try:
        stations = models.Station.objects.filter(geom__distance_lte=(point,Distance(mi=1)))
        stations = stations.distance(point).order_by('distance')
        return stations
    except Exception, e:
        log.warn("Error finding stations near %s: %s" % (point.wkt, e))
        return None    
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import os
import sys

# we want a few paths on the python path
# first up we add the root above the application so
# we can have absolute paths everywhere
python_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../../'
)
# we have have a local apps directory
apps_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../apps'
)
# we have have a local externals directory
# which saves you having to install a load of
# python modules locally and get into a versioning
# issue
ext_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../../ext'
)

# we add them first to avoid any collisions
sys.path.insert(0, python_path)
sys.path.insert(0, apps_path)
sys.path.insert(0, ext_path)

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
__FILENAME__ = settings
import os
import django

# Base paths
DJANGO_ROOT = os.path.dirname(os.path.realpath(django.__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# Debugging
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

# Database
DATABASE_ENGINE = 'postgresql_psycopg2'
DATABASE_NAME = 'hello_newsroom'
DATABASE_USER = 'hello_newsroom'
DATABASE_HOST = 'localhost'
DATABASE_PASSWORD = '5IQZe7WEix'
DATABASE_PORT = '5432'

# Local time
TIME_ZONE = 'America/Chicago'

# Local language
LANGUAGE_CODE = 'en-gb'

# Site framework
SITE_ID = 1

# Internationalization
USE_I18N = False

# Absolute path to the directory that holds media.
MEDIA_ROOT = os.path.join(SITE_ROOT, 'assets')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '%zz*y$4lq&ji+d0==wy9jt$v19l&1#31pj)s_ahy+gtr5vld)#'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
)

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

ROOT_URLCONF = 'hello_newsroom.configs.common.urls'

TEMPLATE_DIRS = (
    os.path.join(SITE_ROOT, 'templates')
)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.humanize',
    'django.contrib.gis',
    'django.contrib.sitemaps',
    'hello_newsroom.apps.core',
)

# Predefined domain
MY_SITE_DOMAIN = 'localhost:8000'

# Email
# run "python -m smtpd -n -c DebuggingServer localhost:1025" to see outgoing
# messages dumped to the terminal
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025
DEFAULT_FROM_EMAIL = 'do.not.reply@tribune.com'

# Caching
CACHE_MIDDLEWARE_KEY_PREFIX='hello_newsroom'
CACHE_MIDDLEWARE_SECONDS=90 * 60 # 90 minutes
CACHE_BACKEND="dummy:///"

# Analytics
OMNITURE_PAGE_NAME = "hello_newsroom"
OMNITURE_SECTION = ""
OMNITURE_SUBSECTION = ""
GOOGLE_ANALYTICS_KEY = ""

GOOGLE_MAPS_API_KEY = "ABQIAAAA3uGjGrzq3HsSSbZWegPbIhSMhkig1Gd5B_2j4H1Xz7hsATFBFhSnBeYqZ7F7xlyJh-_KEClsWgAO6Q" # for all 'amazonaws.com'

# Allow for local (per-user) override
try:
    from local_settings import *
except ImportError:
    pass
########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)', admin.site.root),
    
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT
    }),
    (r'^core/', include('core.urls')),

    (r'^/?', 'django.views.generic.simple.redirect_to', { 'url': 'core/'}),
    
)
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import os
import sys

# we want a few paths on the python path
# first up we add the root above the application so
# we can have absolute paths everywhere
python_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../../'
)
# we have have a local apps directory
apps_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../apps'
)
# we have have a local externals directory
# which saves you having to install a load of
# python modules locally and get into a versioning
# issue
ext_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../../ext'
)

# we add them first to avoid any collisions
sys.path.insert(0, python_path)
sys.path.insert(0, apps_path)
sys.path.insert(0, ext_path)

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
__FILENAME__ = settings
from hello_newsroom.configs.common.settings import *

# Debugging
DEBUG = False
TEMPLATE_DEBUG = DEBUG

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://your-bucket-name.s3.amazonaws.com/hello_newsroom/'

# Predefined domain
MY_SITE_DOMAIN = 'your-ec2-instance-dns-name.amazonaws.com'

# Email
EMAIL_HOST = 'mail'

# Caching
CACHE_BACKEND = 'memcached://127.0.0.1:11211/'

# logging
import logging.config
LOG_FILENAME = os.path.join(os.path.dirname(__file__), 'logging.conf')
logging.config.fileConfig(LOG_FILENAME)
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import os
import sys

# we want a few paths on the python path
# first up we add the root above the application so
# we can have absolute paths everywhere
python_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../../'
)
# we have have a local apps directory
apps_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../apps'
)
# we have have a local externals directory
# which saves you having to install a load of
# python modules locally and get into a versioning
# issue
ext_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../../ext'
)

# we add them first to avoid any collisions
sys.path.insert(0, python_path)
sys.path.insert(0, apps_path)
sys.path.insert(0, ext_path)

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
__FILENAME__ = settings
from hello_newsroom.configs.common.settings import *

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://media-beta.tribapps.com/hello_newsroom/'

# Predefined domain
MY_SITE_DOMAIN = 'ec2-184-73-1-9.compute-1.amazonaws.com'

# Email
EMAIL_HOST = 'localhost'

# Caching
CACHE_BACKEND = 'memcached://127.0.0.1:11211/'

# GOOGLE_MAPS_API_KEY = 'ABQIAAAA3uGjGrzq3HsSSbZWegPbIhSMhkig1Gd5B_2j4H1Xz7hsATFBFhSnBeYqZ7F7xlyJh-_KEClsWgAO6Q' # all amazonaws.com

# If you want to use Django Debug Toolbar, you need to list your IP address here
INTERNAL_IPS = ('0.0.0.0')

# logging
import logging.config
LOG_FILENAME = os.path.join(os.path.dirname(__file__), 'logging.conf')
logging.config.fileConfig(LOG_FILENAME)
########NEW FILE########
