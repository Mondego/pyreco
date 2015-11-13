__FILENAME__ = admin
from django.contrib.admin import TabularInline, StackedInline
from django.conf import settings

INLINE_ORDERING_JS = getattr(settings,
                             'INLINE_ORDERING_JS', 'inline_ordering.js')


class OrderableStackedInline(StackedInline):
    
    """Adds necessary media files to regular Django StackedInline"""
    
    class Media:
        js = (INLINE_ORDERING_JS,)


class OrderableTabularInline(TabularInline):
    
    """Adds necessary media files to regular Django TabularInline"""
    
    class Media:
        js = (INLINE_ORDERING_JS,)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Orderable(models.Model):
    
    """Add extra field and default ordering column for and inline orderable model"""
    
    inline_ordering_position = models.IntegerField(blank = True, 
                                                   null = True, 
                                                   editable = True)
    
    class Meta:
        abstract = True 
        ordering = ('inline_ordering_position',)
    
    def save(self, force_insert=False, force_update=False, using=None):
        """Calculate position (max+1) for new records"""
        if not self.inline_ordering_position:
            max = self.__class__.objects.filter().aggregate(models.Max('inline_ordering_position'))
            try: 
                self.inline_ordering_position = max['inline_ordering_position__max'] + 1
            except TypeError:
                self.inline_ordering_position = 1
        return super(Orderable, self).save(force_insert=force_insert, force_update=force_update, using=using)
########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

# path to inline_ordering.js
INLINE_ORDERING_JS = getattr(settings, 'INLINE_ORDERING_JS', settings.MEDIA_URL + 'inline_ordering.js')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
import os.path 

PROJECT_ROOT = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_ROOT, 'testproject.db'),
        'TEST_NAME': os.path.join(PROJECT_ROOT, 'testproject_test.db'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = True

USE_L10N = True

MEDIA_ROOT = os.path.join(PROJECT_ROOT, '..', 'media')

MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(PROJECT_ROOT, '..', 'static')

STATIC_URL = '/static/'

ADMIN_MEDIA_PREFIX = '/static/admin/'

STATICFILES_DIRS = (
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SECRET_KEY = 'rmg3+5r8=y7az!&tfvd-77j5r^yk@!6nil17%1lxs1wbxp$6&p'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'testproject.urls'

TEMPLATE_DIRS = (
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'admin_jqueryui',
    # Uncomment the next line to enable admin documentation:

    'inline_ordering',
    
    'testapp',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
import models
from inline_ordering.admin import OrderableStackedInline #, OrderableTabularInline


class ImageInline(OrderableStackedInline):
#class ImageInline(OrderableTabularInline):
    
    """
    This _must_ be draggable. Preferably, in future versions, it should allow 
    developer to use either Tabular and Stacked inlines. 
    """
    
    model = models.Image


class TestimonialInline(admin.StackedInline):
#class TestimonialInline(admin.TabularInline):
    
    """
    This _cannot_ be draggable. 
    """
    
    model = models.Testimonial


class GalleryAdmin(admin.ModelAdmin):
    
    model = models.Gallery
    inlines = (ImageInline, TestimonialInline,)
    
#    class Media:
#        js = (
#            'http://ajax.googleapis.com/ajax/libs/jquery/1/jquery.min.js',
#            'http://ajax.googleapis.com/ajax/libs/jqueryui/1/jquery-ui.min.js',
#        )


admin.site.register(models.Gallery, GalleryAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from inline_ordering.models import Orderable


class Gallery(models.Model):
    
    title = models.CharField(max_length=200)
    
    class Meta:
        verbose_name_plural = 'Galleries' # :)
    
    def __unicode__(self):
        return self.title


class Image(Orderable):
    
    gallery = models.ForeignKey(Gallery)
    image = models.ImageField(upload_to='testapp')
    title = models.CharField(max_length=200)
    
    def __unicode__(self):
        return self.title


class Testimonial(models.Model):
    
    gallery = models.ForeignKey(Gallery)
    title = models.CharField(max_length=200)
    content = models.TextField()
########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import include, patterns, url
from django.contrib import admin
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    #url(r'^', include('cms.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('django.contrib.staticfiles.views',
        url(r'^static/(?P<path>.*)$', 'serve'),
    )

########NEW FILE########
