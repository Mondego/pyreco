__FILENAME__ = admin
from django.contrib import admin
from django.utils.safestring import mark_safe
from models import SourceImage, CropSize, CroppedImage

admin.site.register(SourceImage)
admin.site.register(CropSize)

class CroppedImageAdmin(admin.ModelAdmin):
    change_form_template = 'cropper/crop_admin_interface.html'
    
    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            fields = ('source', 'size')
        else:
            fields = ('source', 'size', 'x', 'y', 'w', 'h')
        kwargs['fields'] = fields
        return super(CroppedImageAdmin, self).get_form(request, obj, **kwargs)
    
    def preview_thumb(self, obj):
        if obj.image:
            return mark_safe(
                u'<img src="%s" style="width: 200px">' % obj.image.url
            )
        else:
            return None
    preview_thumb.allow_tags = True
    
    list_display = ('__unicode__', 'size', 'preview_thumb')
    list_filter = ('size',)

admin.site.register(CroppedImage, CroppedImageAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.core.files.base import ContentFile, File
from StringIO import StringIO
import Image, uuid

class SourceImage(models.Model):
    name = models.CharField(max_length = 255, blank = True)
    description = models.TextField(blank = True)
    image = models.ImageField(
        upload_to='sources/%Y/%m', blank = True, max_length=255
    )
    preview = models.ImageField(
        upload_to='preview/%Y/%m', blank = True, max_length=255, editable=0
    )
    url = models.URLField(verify_exists = False, blank = True, help_text="""
    This doesn't do anything yet...
    """.strip())
    
    def save(self, *args, **kwargs):
        if self.image:
            original = Image.open(self.image)
            if original.size[0] > 800:
                preview = original.resize(
                    (800, int(original.size[1] * (800.0 / original.size[0])))
                )
            else:
                preview = original.resize(original.size)
            
            contents = StringIO()
            preview.save(contents, format='jpeg', quality=25)
            self.preview.save(
                '%s.jpg' % str(uuid.uuid4()),
                ContentFile(contents.getvalue()), save=False
            )
        super(SourceImage, self).save(*args, **kwargs)
    
    def __unicode__(self):
        s = u''
        if self.name:
            s = u'%s: ' % self.name
        if self.image:
            s += self.image.url
        else:
            s += self.url
        return s

class CropSize(models.Model):
    name = models.CharField(max_length = 255, blank = True)
    description = models.TextField(blank = True)
    width = models.PositiveSmallIntegerField()
    height = models.PositiveSmallIntegerField()
    
    def __unicode__(self):
        if self.name:
            return u'%sx%s - %s' % (self.width, self.height, self.name)
        else:
            return u'%sx%s' % (self.width, self.height)

class CroppedImage(models.Model):
    source = models.ForeignKey(SourceImage)
    size = models.ForeignKey(CropSize)
    x = models.PositiveSmallIntegerField(null = True, blank = True)
    y = models.PositiveSmallIntegerField(null = True, blank = True)
    w = models.PositiveSmallIntegerField(null = True, blank = True)
    h = models.PositiveSmallIntegerField(null = True, blank = True)
    image = models.ImageField(
        upload_to='crops/%Y/%m', blank = True, max_length=255
    )
    
    def save(self, *args, **kwargs):
        # Crop the image, provided x/y/w/h are available
        if self.x is not None and self.y is not None \
                and self.w is not None and self.h is not None:
            original = Image.open(self.source.image)
            cropped = original.crop(
                # left, upper, right, lower
                (self.x, self.y, (self.x + self.w), (self.y + self.h))
            )
            
            tmp = Image.new('RGB', cropped.size)
            tmp.paste(cropped, (0, 0))
            cropped = tmp
            
            if self.size:
                size_xy = (self.size.width, self.size.height)
                cropped = cropped.resize(
                    size_xy, Image.ANTIALIAS
                )
            contents = StringIO()
            cropped.save(contents, format='jpeg', quality=90)
            contents.seek(0)
            filename = '%s.jpg' % str(uuid.uuid4())
            self.image.save(
                filename,
                ContentFile(contents.getvalue()), save=False
            )
        super(CroppedImage, self).save(*args, **kwargs)
    
    def __unicode__(self):
        return u'%s cropped to %s' % (self.source, self.size)

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
__FILENAME__ = views
# Create your views here.

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
__FILENAME__ = settings
import os, sys

OUR_ROOT = os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.join(OUR_ROOT, '..'))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(OUR_ROOT, 'data.db')
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(OUR_ROOT, 'static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 's6m__ur4psb)pwo8#nmf2m$3qm8+%cl6g4vxbemv8h&ww4*^ie'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'demo_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'cropper',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
import os
from django.contrib import admin
admin.autodiscover()

import cropper

urlpatterns = patterns('',
    # Example:
    # (r'^demo_project/', include('demo_project.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^static/cropper-assets/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': os.path.join(
            os.path.realpath(os.path.dirname(cropper.__file__)), 'assets'
        )
    }),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': os.path.join(settings.OUR_ROOT, 'static'),
    }),
    (r'^admin/(.*)', admin.site.root),
)

########NEW FILE########
