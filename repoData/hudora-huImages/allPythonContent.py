__FILENAME__ = imageserver_import
#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Maximillian Dornseif on 2009-01-29.
Copyright (c) 2009 HUDORA. All rights reserved.
"""

import base64
import datetime
import hashlib
import mimetypes
import time
import couchdb.client

COUCHSERVER = "http://couchdb.local.hudora.biz:5984"
COUCHDB_NAME = "huimages"
# I'm totally out of ideas how to switch between production and test environments


def _datetime2str(d):
    """Converts a datetime object to a usable string."""
    return "%s.%06d" % (d.strftime('%Y%m%dT%H%M%S'), d.microsecond)
    

def _setup_couchdb():
    """Get a connection handler to the CouchDB Database, creating it when needed."""
    server = couchdb.client.Server(COUCHSERVER)
    if COUCHDB_NAME in server:
        return server[COUCHDB_NAME]
    else:
        return server.create(COUCHDB_NAME)
    
def save_image(imagedata, contenttype=None, timestamp=None, title='', references={}, filename='image.jpeg'):    
    db = _setup_couchdb()
    doc_id = "%s01" % base64.b32encode(hashlib.sha1(imagedata).digest()).rstrip('=')

    try:
        doc = db[doc_id]
    except couchdb.client.ResourceNotFound:
        doc = {}

    if not contenttype:
        contenttype = mimetypes.guess_type(filename)    
    if not timestamp:
        timestamp = datetime.datetime.now()
    if hasattr(timestamp, 'strftime'):
        timestamp = _datetime2str(datetime.datetime.now())

    if not 'ctime' in doc:
        doc['ctime'] = timestamp
    doc['mtime'] = timestamp
    for key, value in references.items():
        if value not in doc.get('references', {}).get(key, []):
            doc.setdefault('references', {}).setdefault(key, []).append(value)
    if title and title not in doc.get('title', []):
        doc.setdefault('title', []).append(title)
        
    db[doc_id] = doc
    print db[doc_id]
    if not (doc.get('_attachments')):
        db.put_attachment(db[doc_id], imagedata, filename.lstrip('./'))
    return doc_id


import os
import sys
import datetime
from optparse import OptionParser


def parse_commandline():
    """Parse the commandline and return information."""
    
    parser = OptionParser(version=True)
    parser.set_usage('usage: %prog [options] filename [filename]. Try %prog --help for details.')    
    parser.add_option('--artnr', action='store', type='string')
    parser.add_option('--title', action='store', type='string')
    options, args = parser.parse_args()
    
    print vars(options)
    if len(args) < 1:
        parser.error("incorrect number of arguments")
    return options, args
    

options, args = parse_commandline()

# save_image(i.path.read(), references={"artnr": i.product.artnr}, title=i.title, filename=filename)    
ref={}
if options.artnr:
    ref['artnr'] = options.artnr 
for name in args:
    print name
    print save_image(open(name).read(), references=ref, title=options.title, filename=name,
                     timestamp=datetime.datetime.utcfromtimestamp(os.stat(name).st_mtime))


########NEW FILE########
__FILENAME__ = imagestuff
#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Maximillian Dornseif on August 2006.
Copyright (c) 2006, 2009 HUDORA. All rights reserved.
"""

import Image 
import base64
import cgi
import datetime
import hashlib
import md5
import os
import time
import time
import urlparse
import couchdb.client

# from django.core import urlresolvers
# from django.conf import settings
# from django.utils.html import escape 
# from django.utils.safestring import mark_safe 
# from django.utils.functional import curry
# from django.db.models import ImageField, signals
# 

IMAGESERVER = "http://images.hudora.de"
COUCHSERVER = "http://couchdb.local.hudora.biz:5984"
COUCHDB_NAME = "huimages"

#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Maximillian Dornseif on 2009-01-29.
Copyright (c) 2009 HUDORA. All rights reserved.
"""

import base64
import datetime
import hashlib
import mimetypes
import os.path
import random
import time
import couchdb.client

COUCHSERVER = "http://couchdb.local.hudora.biz:5984"
COUCHDB_NAME = "huimages"
# I'm totally out of ideas how to switch between production and test environments


_sizes = {'mini':    "23x40",
          'thumb':   "50x200", 
          'sidebar': "179x600",
          'small':   "240x160",
          'medium':  "480x320", 
          'full':    "477x800",
          'svga':    "800x600", 
          'xvga':    "1024x768",
          'square':  "75x75!"} 


def _datetime2str(d):
    """Converts a datetime object to a usable string."""
    return "%s.%06d" % (d.strftime('%Y%m%dT%H%M%S'), d.microsecond)
    

def _setup_couchdb():
    """Get a connection handler to the CouchDB Database, creating it when needed."""
    server = couchdb.client.Server(COUCHSERVER)
    if COUCHDB_NAME in server:
        return server[COUCHDB_NAME]
    else:
        return server.create(COUCHDB_NAME)
    
def save_image(imagedata, contenttype=None, timestamp=None, title='', references={}, filename='image.jpeg'):  
  
    db = _setup_couchdb()
    doc_id = "%s01" % base64.b32encode(hashlib.sha1(imagedata).digest()).rstrip('=')

    try:
        doc = db[doc_id]
    except couchdb.client.ResourceNotFound:
        doc = {}

    if not contenttype:
        contenttype = mimetypes.guess_type(filename)    
    if not timestamp:
        timestamp = _datetime2str(datetime.datetime.now())
    if not 'ctime' in doc:
        doc['ctime'] = timestamp
    doc['mtime'] = timestamp
    if 'product_image' not in doc.get('types', []):
        doc.setdefault('types', []).append('product_image')
    for key, value in references.items():
        if value not in doc.get('references', {}).get(key, []):
            doc.setdefault('references', {}).setdefault(key, []).append(value)
    if title and title not in doc.get('title', []):
        doc.setdefault('title', []).append(title)
        
    db[doc_id] = doc
    print db[doc_id]
    if not (doc.get('_attachments')):
        db.put_attachment(db[doc_id], imagedata, filename)
    return doc_id
    

def imageurl(imageid, size='o'):
    return urlparse.urljoin(IMAGESERVER, os.path.join(size, imageid)) + '.jpeg'
    

def scaled_imageurl(imageid, size='square'):
    """Scales an image according to 'size' and returns the URL of the scaled image."""
    return urlparse.urljoin(IMAGESERVER, os.path.join(_sizes.get(size, size), imageid)) + '.jpeg'
    

def scaled_dimensions(imageid, size='square'):
    """Scales an image according to 'size' and returns the dimensions."""
    size = _sizes.get(size, size)
    width, height = size.split('x')
    if size.endswith('!'):
        return (int(width), int(height.rstrip('!')))
    # get current is_width and is_height
    try:
        db = _setup_couchdb()
        doc = db[imageid]
        return _scale(width, height, doc.width, doc.height)
    except:
        return (None, None)
    

def scaled_tag(imageid, size='square', *args, **kwargs):
    """Scales an image according to 'size' and returns an XHTML tag for that image.
    
    Additional keyword arguments are added as attributes to  the <img> tag.
    
    >>> img.path_scaled().svga_tag(alt='neu')
    '<img src="http://images.hudora.de/477x600/0ead6fsdfsaf.jpeg" width="328" height="600" alt="neu"/>'
    """
    ret = ['<img src="%s"' % cgi.escape(scaled_imageurl(imageid, size), True)]
    width, height = scaled_dimensions(imageid, size)
    if width and height:
        ret.append('width="%d" height="%d"' % (width, height))
    ret.extend(args)
    for key, val in kwargs.items():
        ret.append('%s="%s"' % (cgi.escape(key, True), egi.escape(val, True)))
    ret.append('/>')
    return ' '.join(ret)
    

def get_random_imageid():
    db = _setup_couchdb()
    startkey = base64.b32encode(hashlib.sha1(str(random.random())).digest()).rstrip('=')
    return [x.id for x in db.view('_all_docs', startkey=startkey, limit=1)][0]


print '<html><body>'
for y in range(4):
    for x in range(4):
        imageid = get_random_imageid()
        print '<a href="http://couchdb1.local.hudora.biz:5984/_utils/document.html?huimages/%s">%s</a>' % (imageid, scaled_tag(imageid, "200x200!"))
    print '<br/>'
print '</body></html>'


#from produktpass.models import *
#for i in  Image.objects.all():
#    filename = os.path.split(str(i.path))[1]
#    print save_image(i.path.read(), references={"artnr": i.product.artnr}, title=i.title, filename=filename)    



# encoding: utf-8

"""Image field which scales images on demand.

This acts like Django's ImageField but in addition can scale images on demand. Scaled Images are put in
<settings.MEDIA_ROOT>/,/<originalpath>. The avialable scaling factors are hardcoded in the dictionary _sizes.
If the dimensions there are followed by an '!' this means the images should be cropped to exactly this size.
Without this the images are scaled to fit in the given size without changing the aspect ratio of the image.

Scaled versions of the images are generated on the fly using PIL and then kept arround in the Filesystem. 

Given a model like

class Image(models.Model):
    path       = ScaledImageField(verbose_name='Datei', upload_to='-/product/image')
    [...]

you can do  the following:

>>> img.path  
'-/product/image/0e99d6be8ec0259df920c2d273d1ad6f.jpg'
>>>img.get_path_url()
'/media/-/product/image/0e99d6be8ec0259df920c2d273d1ad6f.jpg'
>>> img.get_path_size()
417119L
>>> img.get_path_width()
1584
>>> img.get_path_height()
2889

All well known metods from ImageField are supported. The new functionality is available via img.path_scaled - this returns an
Imagescaler instance beeing able to play some nifty tricks:

>>> img.path_scaled().svga()
'/,/-/product/image/0e99d6be8ec0259df920c2d273d1ad6f.jpg/svga.jpeg'
>>> img.path_scaled().svga_path()
'/usr/local/web/media/,/-/product/image/0e99d6be8ec0259df920c2d273d1ad6f.jpg/svga.jpeg'
>>> img.path_scaled().svga_dimensions()
(328, 600)
>>> img.path_scaled().svga_tag()
'<img src="/,/-/product/image/0e99d6be8ec0259df920c2d273d1ad6f.jpg/svga.jpeg" width="328" height="600" />'
>>> img.path_scaled().thumb_dimensions()
(50, 91)
>>> img.path_scaled().square_dimensions()
(75, 76)

Created August 2006, 2009 by Maximillian Dornseif. Consider it BSD licensed.
"""



def _scale(want_width, want_height, is_width, is_height):
    """
    This function will scale an image to a given bounding box. Image
    aspect ratios will be conserved and so there might be blank space
    at two sides of the image if the ratio isn't identical to that of
    the bounding box.
    
    Returns the size of the final image.
    """
    # from http://simon.bofh.ms/cgi-bin/trac-django-projects.cgi/file/stuff/branches/magic-removal/image.py
    lfactor = 1    
    width, height = int(want_width), int(want_width)
    if is_width > width and is_height > height:
        lfactorx = float(width) / float(is_width)
        lfactory = float(height) / float(is_height)
        lfactor = min(lfactorx, lfactory)
    elif is_width > width:
        lfactor = float(width) / float(is_width)
    elif is_height > height:
        lfactor = float(height) / float(is_height)
    return (int(float(width) * lfactor), int(float(height) * lfactor))
    

class Imagescaler:
    """Class whose instances scale an image on the fly to desired properties.
    
    For each set of dimensions defined in _sizes imagescaler has a set of functions, e.g. for 'small':
    
    o.small() = return the URL of the small version of the image
    o.small_path() - return the absolute  pathe in the filesystem for the  image
    o.small_dimensions() - return (width,  heigth)
    o.small_tag() - return a complete image tag for use in XHTML
    
    >>> img.path_scaled().svga()
    '/,/-/product/image/0e99d6be8ec0259df920c2d273d1ad6f.jpg/svga.jpeg'
    >>> img.path_scaled().svga_path()
    '/usr/local/web/media/,/-/product/image/0e99d6be8ec0259df920c2d273d1ad6f.jpg/svga.jpeg'
    >>> img.path_scaled().svga_dimensions()
    (328, 600)
    >>> img.path_scaled().svga_tag()
    '<img src="/,/-/product/image/0e99d6be8ec0259df920c2d273d1ad6f.jpg/svga.jpeg" width="328" height="600" />'
    """
    def __init__(self, field, obj):
        self.field = field
        self.parent_obj = obj
        self.original_image = getattr(self.parent_obj, self.field.attname)
        # if broken.gif exists we sendd that if there are any problems during scaling
        if not os.path.exists(self.original_image_path):
            self.broken_image = os.path.join(settings.MEDIA_ROOT, 'broken.gif') 
        for size in _sizes:
            setattr(self, '%s' % (size), curry(self.scaled_url, size))
            setattr(self, '%s_dimensions' % (size), curry(self.scaled_dimensions, size))
            setattr(self, '%s_tag' % (size), curry(self.scaled_tag, size))
    
    def scaled_url(self, size='thumb'):
        """Scales an image according to 'size' and returns the URL of the scaled image."""
        return urlparse.urljoin(IMAGESERVER, _sizes.get(size, size), self.imageid) + '.jpeg'
    
    def scaled_dimensions(self, size='thumb'):
        """Scales an image according to 'size' and returns the dimensions."""
        size = _sizes.get(size, size)
        width, height = [int(i) for i in _sizes[size].split('x')]
        if size.endswith('!'):
            return (width, height)
        # get current is_width and is_height
        try:
            db = _setup_couchdb()
            doc = db[doc_id]
            return _scale(width, height, doc.width, doc.height)
        except:
            return (None, None)
    
    def scaled_tag(self, size='thumb', *args, **kwargs):
        """Scales an image according to 'size' and returns an XHTML tag for that image.
        
        Additional keyword arguments are added as attributes to  the <img> tag.
        
        >>> img.path_scaled().svga_tag(alt='neu')
        '<img src="http://images.hudora.de/477x600/0ead6fsdfsaf.jpeg" width="328" height="600" alt="neu"/>'
        """
        ret = ['<img src="%s"' % escape(self.scaled_url(size))]
        width, height = self.scaled_dimensions(size)
        if width and height:
            ret.append('width="%d" height="%d"' % (width, height))
        ret.extend(args)
        for key, val in kwargs.items():
            ret.append('%s="%s"' % (escape(key), escape(val)))
        ret.append('/>')
        return mark_safe(' '.join(ret))


#class ScalingImageField(ImageField):
#    """This acts like Django's ImageField but in addition can scale images on demand by providing an
#    ImageScler object.
#    
#    >>> img.path_scaled().svga()
#    '/,/-/product/image/0e99d6be8ec0259df920c2d273d1ad6f.jpg/svga.jpeg'
#    """
#    
#    def __init__(self, verbose_name=None, name=None, width_field=None, height_field=None, auto_rename=True,
#                 **kwargs):
#        """Inits the ScalingImageField."""
#        super(ScalingImageField, self).__init__(verbose_name, name, width_field, height_field, **kwargs)
#    
#    def contribute_to_class(self, cls, name):
#        """Adds field-related functions to the model."""
#        super(ScalingImageField, self).contribute_to_class(cls, name)
#        setattr(cls, '%s_scaled' % self.name, curry(Imagescaler, self))
#    
#    def get_internal_type(self):
#        return 'ImageField'
#
#
#
#if __name__ == '__main__':
#    unittest.main()
    
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
__FILENAME__ = middleware
#!/usr/bin/env python
# encoding: utf-8
"""
middleware.py tracks clients by setting a persistent coockie.

You can access it via request.clienttrack_uid.

Created by Maximillian Dornseif on 2009-02-07.
Copyright (c) 2009 HUDORA. All rights reserved.
"""

import time
import base64
import hashlib
import random
from django.utils.http import cookie_date

class ClienttrackMiddleware(object):
    def process_request(self, request):
        if '_hda' in request.COOKIES:
            request.clienttrack_first_visit, request.clienttrack_uid =  request.COOKIES.get('_hda').split(',')[:2]
        else:
            request.clienttrack_uid = base64.b32encode(hashlib.md5("%f-%f" % (random.random(), time.time())).digest()).rstrip('=')
            request.clienttrack_first_visit = None
    
    def process_response(self, request, response):
        if not request.clienttrack_first_visit:
                max_age = 3*365*24*60*60  # 3 years
                expires_time = time.time() + max_age
                expires = cookie_date(expires_time)
                response.set_cookie('_hda', "%d,%s" % (time.time(), request.clienttrack_uid),
                                    max_age=max_age, expires=expires)
        return response

########NEW FILE########
__FILENAME__ = settings
# Django settings for huImages_test project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'z2mls53rh)phe%zq^h$s7+r7jkjw_oacrfb3xsb6(a(w_7=dq='

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'middleware.ClienttrackMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    '.',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'imagebrowser',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    (r'^images/', include('imagebrowser.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    #(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    #(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = forms
from django import forms


class UploadForm(forms.Form):
    title = forms.CharField(required=False)
    tags = forms.CharField(required=False)
    image = forms.ImageField()

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^upload/api/', 'huimages.imagebrowser.views.api_store_image'),
    (r'^upload/swfupload.swf', 'huimages.imagebrowser.views.upload_serve_swffile'),
    (r'^upload/', 'huimages.imagebrowser.views.upload'),
    (r'^image/random/', 'huimages.imagebrowser.views.random_image'),
    (r'^image/(?P<imageid>.+)/previous/', 'huimages.imagebrowser.views.previous_image'),
    (r'^image/(?P<imageid>.+)/next/', 'huimages.imagebrowser.views.next_image'),
    (r'^image/(?P<imageid>.+)/rate/', 'huimages.imagebrowser.views.rate'),
    (r'^image/(?P<imageid>.+)/favorite/', 'huimages.imagebrowser.views.favorite'),
    (r'^image/(?P<imageid>.+)/tag/', 'huimages.imagebrowser.views.tag'),
    (r'^image/(?P<imageid>.+)/update_title/', 'huimages.imagebrowser.views.update_title'),
    (r'^image/(?P<imageid>.+)/tag_suggestion/', 'huimages.imagebrowser.views.tag_suggestion'),
    url(r'^image/(?P<imageid>.+)/', 'huimages.imagebrowser.views.image', name='view-image'),
    (r'^favorites/(?P<uid>.+)/$', 'huimages.imagebrowser.views.favorites'),
    (r'^favorites/$', 'huimages.imagebrowser.views.favorites_redirect'),
    (r'^tag/(?P<tagname>.+)/', 'huimages.imagebrowser.views.by_tag'),
    (r'^$', 'huimages.imagebrowser.views.startpage'),
)

########NEW FILE########
__FILENAME__ = views
#!/usr/bin/env python
# encoding: utf-8
"""
imagebrowser/views.py

Created by Maximillian Dornseif on 2009-01-29.
Copyright (c) 2009, 2010 HUDORA. All rights reserved.
"""


import couchdb.client
import os
from operator import itemgetter
from huTools.async import Future
from huTools.decorators import cache_function

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.safestring import mark_safe
from django.utils import simplejson
from django.core.urlresolvers import reverse

from huimages import *
from huimages.imagebrowser.forms import UploadForm

IMAGESERVER = "http://i.hdimg.net"
COUCHSERVER = "http://couchdb.local.hudora.biz:5984"
COUCHDB_NAME = "huimages"

# helpers

def get_rating(imageid):
    server = couchdb.client.Server(COUCHSERVER)
    db = server[COUCHDB_NAME + '_meta']
    ret = [x.value for x in db.view('ratings/all', startkey=imageid, limit=1) if x.key == imageid]
    if ret:
        votecount = ret[0][0]
        return votecount, float(ret[0][1]) / votecount
    else:
        return 0, 0


def get_user_tags(imageid, userid):
    """Returns a list of user specific tags"""
    server = couchdb.client.Server(COUCHSERVER)
    db = server[COUCHDB_NAME + '_meta']
    doc_id = "%s-%s" % (imageid, userid)
    return db.get(doc_id, {}).get('tags', [])


def get_all_tags(imageid):
    """Return a list of all tags for an image"""
    server = couchdb.client.Server(COUCHSERVER)
    db = server[COUCHDB_NAME + '_meta']
    doc_id = imageid
    tags = set([x.value for x in db.view('tags/tags_per_document', startkey=imageid, endkey="%sZ" % imageid)])
    return list(tags)


def is_favorite(imageid, userid):
    server = couchdb.client.Server(COUCHSERVER)
    db = server[COUCHDB_NAME + '_meta']
    doc_id = "%s-%s" % (imageid, userid)
    return db.get(doc_id, {}).get('favorite', False)


@cache_function(60)
def get_tagcount():
    server = couchdb.client.Server(COUCHSERVER)
    db = server[COUCHDB_NAME + '_meta']
    ret = dict([(x.key, x.value) for x in db.view('tags/tagcount', group=True)])
    return ret


def update_user_metadata(imageid, userid, data):
    server = couchdb.client.Server(COUCHSERVER)
    db = server[COUCHDB_NAME + '_meta']

    doc_id = "%s-%s" % (imageid, userid)
    doc = {'imageid': imageid, 'userid': userid}
    doc.update(data)
    open('/tmp/debug3.txt', 'a').write(repr([doc_id]))

    try:
        db[doc_id] = doc
    except couchdb.client.http.ResourceConflict:
        doc = db[doc_id]
        doc.update(data)
        db[doc_id] = doc


def images_by_tag(tagname):
    """Returns ImageIds with a certain tag."""
    server = couchdb.client.Server(COUCHSERVER)
    db = server[COUCHDB_NAME + '_meta']
    ret = [x.value for x in db.view('tags/document_per_tag', startkey=tagname, endkey="%sZ" % tagname)]
    return ret


def get_favorites(uid):
    server = couchdb.client.Server(COUCHSERVER)
    db = server[COUCHDB_NAME + '_meta']
    ret = [x.value for x in db.view('favorites/all', startkey=uid, endkey="%sZ" % uid)]
    return ret


def set_tags(newtags, imageid, userid):
    open('/tmp/debug2.txt', 'a').write(repr([newtags, imageid, userid]))
    newtags = newtags.lower().replace(',', ' ').split(' ')
    newtags = [x.strip() for x in newtags if x.strip()]
    tags = set(get_user_tags(imageid, userid) + newtags)
    tags = [x.lower() for x in list(tags) if x]
    open('/tmp/debug2.txt', 'a').write(repr([tags]))
    update_user_metadata(imageid, userid, {'tags': tags})
    return newtags


# views

def startpage(request):
    def get_line():
        line = []
        for dummy in range(5):
            imageid = get_random_imageid()
            line.append(mark_safe('<a href="image/%s/">%s</a>' % (imageid, scaled_tag(imageid, "150x150!"))))
        return line

    tagfuture = Future(get_tagcount)
    linef = []
    for dummy in range(3):
        linef.append(Future(get_line))
    tagcount = sorted(tagfuture().items())
    lines = []
    for line in linef:
        lines.append(line())
    return render_to_response('imagebrowser/startpage.html', {'lines': lines, 'tags': tagcount,
                              'title': 'HUDORA Bilderarchiv'},
                                context_instance=RequestContext(request))


def upload(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = request.FILES['image']
            imageid = save_image(image.read(), title=form.cleaned_data.get('title'))
            set_tags(form.cleaned_data.get('tags'), imageid, request.clienttrack_uid)
            return HttpResponseRedirect(reverse('view-image', kwargs={'imageid': imageid}))
    else:
        form = UploadForm()
    return render_to_response('imagebrowser/upload.html', {'form': form, 'title': 'Bilder Upload',
                                                           'clienttrack': request.clienttrack_uid},
                                context_instance=RequestContext(request))


def api_store_image(request):
    if request.method == 'POST':
        if request.FILES:
            image = request.FILES['uploadfile']
            imageid = save_image(image.read(), title=request.GET.get('title', ''))
            set_tags(request.GET.get('tags', ''), imageid, request.GET.get('clienttrack', 'API'))
            return HttpResponse(imageid)
    raise Http404


def upload_serve_swffile(request):
    """Server the Shopwave uploader - should be served from the same path as the upload destination."""
    ret = HttpResponse(mimetype="application/xhtml+xml")
    fd = open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'swfupload.swf'))
    ret.write(fd.read(), mimetype='application/x-shockwave-flash')
    return ret


def favorites_redirect(request):
    """Redirects to the user specific favorites page."""
    return HttpResponseRedirect("%s/" % request.clienttrack_uid)


def favorites(request, uid):
    ret = get_favorites(uid, request)
    lines = []
    while ret:
        line = []
        for dummy in range(5):
            if ret:
                imageid = ret.pop()
                line.append(mark_safe('<a href="/i/image/%s/">%s</a>' % (imageid,
                            scaled_tag(imageid, "150x150!"))))
        lines.append(line)
    return render_to_response('imagebrowser/collection.html', {'lines': lines, 'title': 'Ihre Favoriten'},
                                context_instance=RequestContext(request))


def by_tag(request, tagname):
    ret = images_by_tag(tagname)
    lines = []
    while ret:
        line = []
        for dummy in range(5):
            if ret:
                imageid = ret.pop()
                line.append(mark_safe('<a href="/i/image/%s/">%s</a>' % (imageid,
                            scaled_tag(imageid, "150x150!"))))
        lines.append(line)
    return render_to_response('imagebrowser/collection.html', {'lines': lines, 'title': 'Tag "%s"' % tagname},
                                context_instance=RequestContext(request))


def image(request, imageid):
    imagetag = mark_safe('<a href="%s">%s</a>' % (imageurl(imageid), scaled_tag(imageid, "vga")))
    imagedoc = get_imagedoc(imageid)
    votecount, rating = get_rating(imageid)
    favorite = is_favorite(imageid, request.clienttrack_uid)
    tags = get_all_tags(imageid)
    previousid = get_previous_imageid(imageid)
    nextid = get_next_imageid(imageid)
    return render_to_response('imagebrowser/image.html', {'imagetag': imagetag,
         'favorite': favorite, 'tags': tags, 'rating': rating,
        'previous': mark_safe('<a href="../../image/%s/">%s</a>' % (previousid,
                              scaled_tag(previousid, "75x75!"))),
        'next': mark_safe('<a href="../../image/%s/">%s</a>' % (nextid, scaled_tag(nextid, "75x75!"))),
        'title': imagedoc.get('title', ['ohne Titel'])[-1]},
                                context_instance=RequestContext(request))


def previous_image(request, imageid):
    return HttpResponseRedirect("../../%s/" % get_previous_imageid(imageid))


def random_image(request):
    return HttpResponseRedirect("../%s/" % get_random_imageid())


def next_image(request, imageid):
    return HttpResponseRedirect("../../%s/" % get_next_imageid(imageid))


def tag_suggestion(request, imageid):
    prefix = request.GET.get('tag', '')
    tagcount = list(get_tagcount().items())
    tagcount.sort(key=itemgetter(1), reverse=True)
    json = simplejson.dumps([x[0] for x in tagcount if x[0].startswith(prefix)])
    response = HttpResponse(json, mimetype='application/json')
    return response

# AJAX bookmarking

def favorite(request, imageid):
    if request.POST['rating'] == '1':
        update_user_metadata(imageid, request.clienttrack_uid, {'favorite': True})
    else:
        update_user_metadata(imageid, request.clienttrack_uid, {'favorite': False})
    return HttpResponse('ok', mimetype='application/json')


# AJAX rating

def rate(request, imageid):
    update_user_metadata(imageid, request.clienttrack_uid, {'rating': int(request.POST['rating'])})
    votecount, rating = get_rating(imageid)
    json = simplejson.dumps(rating)
    response = HttpResponse(json, mimetype='application/json')
    return response

def tag(request, imageid):
    """Set tags via AJAX."""
    newtags = request.POST['newtag']
    userid = request.clienttrack_uid
    newtags = set_tags(newtags, imageid, userid)
    # todo: flush tag cache
    json = simplejson.dumps(newtags)
    response = HttpResponse(json, mimetype='application/json')
    return response


# AJAX titeling

def update_title(request, imageid):
    set_title(imageid, request.POST['value'])
    response = HttpResponse(request.POST['value'], mimetype='text/plain')
    return response

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Serving of Images from CouchDB or Amazon S3 with scaling.

Is meant to run with lighttpd for fast serving and cache friendly headers.
/etc/lighttpd/lighttpd.conf should look like examples/lighttpd.conf

If you start getting low on disk space, delete the oldest files in
/usr/local/huImages/cache/
"""

# Created 2006, 2009 by Maximillian Dornseif. Consider it BSD licensed.

import Image
import boto
import boto.s3.connection
import boto.s3.key
import couchdb.client
import os
import os.path
import re
import tempfile
from wsgiref.simple_server import make_server
from flup.server.fcgi_fork import WSGIServer

# This tool needs keeys being set at the shell:
# export AWS_ACCESS_KEY_ID='AKIRA...Z'
# export AWS_SECRET_ACCESS_KEY='hal6...7'

S3BUCKET = os.environ.get('HUIMAGES3BUCKET',
                          os.environ.get('S3BUCKET', 'originals.i.hdimg.net'))
COUCHSERVER = os.environ.get('HUIMAGESCOUCHSERVER',
                             os.environ.get('COUCHSERVER', 'http://127.0.0.1:5984'))
CACHEDIR = os.path.abspath('../cache')
COUCHDB_NAME = "huimages"
typ_re = re.compile('^(o|\d+x\d+!?)$')
docid_re = re.compile('^[A-Z0-9]+$')


def _scale_image(width, height, image):
    """
    This function will scale an image to a given bounding box. Image
    aspect ratios will be conserved and so there might be blank space
    at two sides of the image if the ratio isn't identical to that of
    the bounding box.
    """
    # originally from
    # http://simon.bofh.ms/cgi-bin/trac-django-projects.cgi/file/stuff/branches/magic-removal/image.py
    lfactor = 1
    width, height = int(width), int(height)
    (xsize, ysize) = image.size
    if xsize > width and ysize > height:
        lfactorx = float(width) / float(xsize)
        lfactory = float(height) / float(ysize)
        lfactor = min(lfactorx, lfactory)
    elif xsize > width:
        lfactor = float(width) / float(xsize)
    elif ysize > height:
        lfactor = float(height) / float(ysize)
    res = image.resize((int(float(xsize) * lfactor), int(float(ysize) * lfactor)), Image.ANTIALIAS)
    return res


def _crop_image(width, height, image):
    """
    This will crop the largest block out of the middle of an image
    that has the same aspect ratio as the given bounding box. No
    blank space will be in the thumbnail, but the image isn't fully
    visible due to croping.
    """
    # origially from
    # http://simon.bofh.ms/cgi-bin/trac-django-projects.cgi/file/stuff/branches/magic-removal/image.py
    width, height = int(width), int(height)
    lfactor = 1
    (xsize, ysize) = image.size
    if xsize > width and ysize > height:
        lfactorx = float(width) / float(xsize)
        lfactory = float(height) / float(ysize)
        lfactor = max(lfactorx, lfactory)
    newx = int(float(xsize) * lfactor)
    newy = int(float(ysize) * lfactor)
    res = image.resize((newx, newy), Image.ANTIALIAS)
    leftx = 0
    lefty = 0
    rightx = newx
    righty = newy
    if newx > width:
        leftx += (newx - width) / 2
        rightx -= (newx - width) / 2
    elif newy > height:
        lefty += (newy - height) / 2
        righty -= (newy - height) / 2
    res = res.crop((leftx, lefty, rightx, righty))
    return res


def mark_broken(doc_id):
    """If there is a Problem with an Image, mark it as broken (deleted) in the Database."""
    db = couchdb.client.Server(COUCHSERVER)[COUCHDB_NAME]
    doc = db[doc_id]
    doc['deleted'] = True
    db[doc_id] = doc


def imagserver(environ, start_response):
    """Simple WSGI complient Server."""
    parts = environ.get('PATH_INFO', '').split('/')
    if len(parts) < 3:
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return ["File not found\n"]
    typ, doc_id = parts[1:3]
    doc_id = doc_id.strip('jpeg.')
    if not typ_re.match(typ):
        start_response('501 Error', [('Content-Type', 'text/plain')])
        return ["Not Implemented\n"]
    if not docid_re.match(doc_id):
        start_response('501 Error', [('Content-Type', 'text/plain')])
        return ["Not Implemented\n"]

    if not os.path.exists(os.path.join(CACHEDIR, typ)):
        os.makedirs(os.path.join(CACHEDIR, typ))

    cachefilename = os.path.join(CACHEDIR, typ, doc_id + '.jpeg')
    if os.path.exists(cachefilename):
        # serve request from cache
        start_response('200 OK', [('Content-Type', 'image/jpeg'),
                                  ('Cache-Control', 'max-age=1728000, public'),  # 20 Days
                                  ])
        return open(cachefilename)

    # get data from database
    orgfile = _get_original_file(doc_id)
    if not orgfile:
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return ["File not found"]

    if typ == 'o':
        imagefile = orgfile
    else:
        width, height = typ.split('x')
        try:
            img = Image.open(orgfile)
            if img.mode != "RGB":
                img = img.convert("RGB")
            if height.endswith('!'):
                height = height.strip('!')
                img = _crop_image(width, height, img)
            else:
                img = _scale_image(width, height, img)
        except IOError:
            # we assume the source file is broken
            mark_broken(doc_id)
            start_response('404 Internal Server Error', [('Content-Type', 'text/plain')])
            return ["File not found"]

        tempfilename = tempfile.mktemp(prefix='tmp_%s_%s' % (typ, doc_id), dir=CACHEDIR)
        img.save(tempfilename, "JPEG")
        os.rename(tempfilename, cachefilename)
        # using X-Sendfile could speed this up.
        imagefile = open(cachefilename)

    start_response('200 OK', [('Content-Type', 'image/jpeg'),
                              ('Cache-Control', 'max-age=17280000, public'),  # 20 Days
                              ])
    return imagefile


def save_imagserver(environ, start_response):
    """Executes imageserver() returning a 500 status code on an exception."""
    try:
        return imagserver(environ, start_response)
    except:
        raise
        try:
            start_response('500 OK', [('Content-Type', 'text/plain')])
        except:
            pass
        return ['Error']


def _get_original_file(doc_id):
    """Returns a filehandle for the unscaled file related to doc_id."""

    cachefilename = os.path.join(CACHEDIR, 'o', doc_id + '.jpeg')
    if os.path.exists(cachefilename):
        # File exists in the cache
        return open(cachefilename)

    # ensure the needed dirs exist
    if not os.path.exists(os.path.join(CACHEDIR, 'o')):
        os.makedirs(os.path.join(CACHEDIR, 'o'))

    # try to get file from S3
    conn = boto.connect_s3()
    s3bucket = conn.get_bucket(S3BUCKET, validate=False)
    k = s3bucket.get_key(doc_id)
    if k:
        # write then rename to avoid race conditions
        tempfilename = tempfile.mktemp(prefix='tmp_%s_%s' % ('o', doc_id), dir=CACHEDIR)
        k.get_file(open(tempfilename, "w"))
        os.rename(tempfilename, cachefilename)
        return open(cachefilename)

    # try to get it from couchdb
    db = couchdb.client.Server(COUCHSERVER)[COUCHDB_NAME]
    try:
        doc = db[doc_id]
    except couchdb.client.ResourceNotFound:
        return None

    filename = list(doc['_attachments'].keys())[0]

    # save original Image in Cache
    filedata = db.get_attachment(doc_id, filename)
    # write then rename to avoid race conditions
    tempfilename = tempfile.mktemp(prefix='tmp_%s_%s' % ('o', doc_id), dir=CACHEDIR)
    open(os.path.join(tempfilename), 'w').write(filedata)
    os.rename(tempfilename, cachefilename)

    # upload to S3 for migrating form CouchDB to S3
    conn = boto.connect_s3()
    k = s3bucket.get_key(doc_id)
    if not k:
        k = boto.s3.key.Key(s3bucket)
        k.key = doc_id
        k.set_contents_from_filename(cachefilename)
        k.make_public()

    return open(cachefilename)


standalone = False
if standalone:
    PORT = 8080
    httpd = make_server('', PORT, imagserver)
    print 'Starting up HTTP server on port %i...' % PORT

    # Respond to requests until process is killed
    httpd.serve_forever()

# FastCGI
WSGIServer(save_imagserver).run()

########NEW FILE########
__FILENAME__ = imageserver_import
#!/usr/bin/env python
# encoding: utf-8
"""
imageserver_import.py

Created by Maximillian Dornseif on 2009-01-29.
Copyright (c) 2009 HUDORA. All rights reserved.
"""

import base64
import datetime
import hashlib
import mimetypes
import time
import couchdb.client
import os
import sys
import datetime
from optparse import OptionParser
import huimages

COUCHSERVER = "http://couchdb.local.hudora.biz:5984"
COUCHDB_NAME = "huimages"
# I'm totally out of ideas how to switch between production and test environments


def _datetime2str(d):
    """Converts a datetime object to a usable string."""
    return "%s.%06d" % (d.strftime('%Y%m%dT%H%M%S'), d.microsecond)
    

def _setup_couchdb():
    """Get a connection handler to the CouchDB Database, creating it when needed."""
    server = couchdb.client.Server(COUCHSERVER)
    if COUCHDB_NAME in server:
        return server[COUCHDB_NAME]
    else:
        return server.create(COUCHDB_NAME)
    

def parse_commandline():
    """Parse the commandline and return information."""
    
    parser = OptionParser(version=True)
    parser.set_usage('usage: %prog [options] filename [filename]. Try %prog --help for details.')
    parser.add_option('--artnr', action='store', type='string')
    parser.add_option('--title', action='store', type='string')
    options, args = parser.parse_args()
    
    print vars(options)
    if len(args) < 1:
        parser.error("incorrect number of arguments")
    return options, args
    

options, args = parse_commandline()

# save_image(i.path.read(), references={"artnr": i.product.artnr}, title=i.title, filename=filename)
ref={}
if options.artnr:
    ref['artnr'] = options.artnr
for name in args:
    print name
    print save_image(open(name).read(), references=ref, title=options.title, filename=name,
                     timestamp=datetime.datetime.utcfromtimestamp(os.stat(name).st_mtime))


########NEW FILE########
__FILENAME__ = imageserver_massimport
#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Maximillian Dornseif on August 2006.
Copyright (c) 2006, 2009 HUDORA. All rights reserved.
"""


import Image 
import base64
import cgi
import couchdb.client
import datetime
import hashlib
import md5
import mimetypes
import os
import os.path
import random
import time
import urlparse
import os
from os.path import join, getsize
import re
import huimages


COUCHDB_NAME = "huimages"
COUCHSERVER = "http://couchdb.local.hudora.biz:5984"
IMAGESERVER = "http://i.hdimg.net"


def main(startpath):
    for root, dirs, files in os.walk(startpath):
        print "#", root
        for filenameraw in files:
            filename = re.sub('[^\x00-\x7f]+', '_', filenameraw)
            if filename.lower().endswith('jpeg') \
                or filename.lower().endswith('jpg'):
                #or file.lower().endswith('tiff') \
                #or file.lower().endswith('tif'):
                if 'mobotix' in filename or filename.startswith('.'):
                    continue
                filepath = os.path.join(root, filenameraw)
                print filepath, filename
                try:
                    print huimages.save_image(open(filepath).read(),
                        timestamp=datetime.datetime.utcfromtimestamp(os.stat(filepath).st_mtime),
                        title=filename,
                        references={'path': re.sub('[^\x00-\x7f]+', '_', root)}, filename=filename)
                except Exception, msg:
                    print "*error*", msg

main('/tank/archive/Bilder/')
#main('/tank/fileserver/intranet3')

########NEW FILE########
